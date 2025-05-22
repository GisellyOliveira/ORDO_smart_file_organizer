import argparse
import logging
import sys
import shutil
from pathlib import Path # To manipulate paths and files
import hashlib
from typing import Optional

# --- Logging Configuration ---
# Basic logging setup to output messages to the console.
# The log level is INFO by default but can be changed via command-line arguments.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout) # Log to console
    ]
)
logger = logging.getLogger(__name__) # Logger specific to this module

# --- Extension to Folder Mapping ---
# This dictionary defines how files are categorized based on their extensions.
# Only files with extensions present in this map will be processed by the organizer.
# Keys are file extensions (lowercase, with a leading dot).
# Values are the names of the subfolders to be created in the destination directory.
EXTENSION_MAP = {
    # Text & Documents
    '.txt': "TextFiles",
    '.pdf': "Documents",
    '.docx': "Documents",
    '.doc': "Documents",
    '.odt': "Documents",
    '.rtf': "Documents",
    # Ebooks
    '.epub': "Ebooks",
    '.mobi': "Ebooks",
    # Spreadsheets
    '.xlsx': "Spreadsheets",
    '.xls': "Spreadsheets",
    '.ods': "Spreadsheets",
    # Data Files
    '.csv': "Data",
    '.json': "Data", # Often used for data interchange
    '.xml': "Data",   # Also common for data
    # Images
    '.jpg': "Images",
    '.jpeg': "Images",
    '.png': "Images",
    '.gif': "Images",
    '.bmp': "Images",
    '.tiff': "Images",
    '.webp': "Images",
    '.heic': "Images", # High Efficiency Image File Format (Apple)
    # Vector Graphics & Design
    '.svg': "VectorGraphics",
    '.psd': "Design_Files", # Adobe Photoshop
    '.ai': "Design_Files",  # Adobe Illustrator
    # Archives
    '.zip': "Archives",
    '.rar': "Archives",
    '.tar': "Archives",
    '.gz': "Archives",  # Gzip
    '.7z': "Archives",  # 7-Zip
    # Executables & Installers
    '.exe': "Executables_Installers", # Windows executable
    '.msi': "Executables_Installers", # Windows installer
    '.dmg': "Executables_Installers", # macOS disk image
    '.pkg': "Executables_Installers", # macOS installer package
    '.deb': "Executables_Installers", # Debian/Ubuntu package
    '.rpm': "Executables_Installers", # Red Hat/Fedora package
    '.jar': "Executables_Installers", # Java archive (can be executable)
    # Audio
    '.mp3': "Music", # Specifically for music, common usage
    '.wav': "Audio",
    '.aac': "Audio",
    '.flac': "Audio", # Lossless audio
    '.ogg': "Audio",  # Ogg Vorbis
    '.m4a': "Audio",  # Apple MPEG-4 Audio
    # Videos
    '.mp4': "Videos",
    '.avi': "Videos",
    '.mkv': "Videos", # Matroska
    '.mov': "Videos", # Apple QuickTime
    '.wmv': "Videos", # Windows Media Video
    '.flv': "Videos", # Flash Video
    # Logs & Configs
    '.log': "LogFiles",
    '.yaml': "Configs",
    '.yml': "Configs",
    # Fonts
    '.ttf': "Fonts", # TrueType Font
    '.otf': "Fonts", # OpenType Font
}

class FileOrganizer:
    """
    Organizes files from a source directory into categorized subdirectories
    within a specified destination directory.

    The organization process is recursive, meaning it scans all subfolders
    within the source directory. Files are categorized based on their extensions
    as defined in `EXTENSION_MAP`. The script handles potential duplicate files
    by comparing hashes: identical files (same name, same content) are skipped,
    while files with the same name but different content are renamed before moving.
    """

    def __init__(self, source_dir: Path, dest_dir: Path, dry_run: bool = False):
        """
        Initializes the FileOrganizer.

        Args:
            source_dir: The `pathlib.Path` object representing the source directory
                        containing files to be organized.
            dest_dir: The `pathlib.Path` object representing the base destination
                      directory where categorized subfolders will be created.
            dry_run: If True, the organizer will simulate the organization process
                     (logging intended actions) without making any actual changes
                     to the file system. Defaults to False.

        Raises:
            ValueError: If `source_dir` does not exist or is not a directory,
                        or if `dest_dir` exists but is not a directory.
        """
        if not source_dir.is_dir():
            raise ValueError(f"Source directory does not exist or is not a directory: {source_dir}")
        if dest_dir.exists() and not dest_dir.is_dir():
            # Prevent attempting to organize into a path that exists and is a file.
            raise ValueError(f"Destination path exists but is not a directory: {dest_dir}")

        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.dry_run = dry_run
        self.files_successfully_moved_or_renamed = 0
        self.skipped_identical_duplicates = 0
        # Initialize the session-specific extension map as a copy of the global default.
        # This map can be updated during the organize() method based on user input
        # for the current session.
        self.session_extension_map = EXTENSION_MAP.copy() 
        logger.info(
            f"Organizer initialized. Source: '{self.source_dir}', "
            f"Destination: '{self.dest_dir}', Dry Run: {self.dry_run}"
        )


    def _calculate_file_hash(self, file_path: Path, hash_algo: str = "sha256", buffer_size: int = 65536) -> Optional[str]:
        """
        Calculates the hash of a file using the specified algorithm.

        Reads the file in chunks to handle large files efficiently.

        Args:
            file_path: The `pathlib.Path` to the file.
            hash_algo: The hashing algorithm to use (e.g., "md5", "sha256").
                       Defaults to "sha256".
            buffer_size: The size of chunks (in bytes) to read from the file.
                         Defaults to 65536 (64KB).

        Returns:
            The hexadecimal hash string of the file, or `None` if an error
            occurs during file reading or hash calculation (e.g., file not found,
            permission error).
        """
        hasher = hashlib.new(hash_algo)
        try:
            with file_path.open('rb') as f: # Use Path.open() for consistency
                while True:
                    data = f.read(buffer_size)
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()
        except FileNotFoundError:
            logger.error(f"Hash calculation: File not found at {file_path}")
            return None
        except OSError as e:
            logger.error(f"Hash calculation: OS error reading file {file_path}: {e}")
            return None
        except Exception as e: # Catch any other unexpected errors during hashing
            logger.error(f"Hash calculation: Unexpected error for file {file_path}: {e}", exc_info=True)
            return None

    def _get_destination_folder_or_ignore(self, file_path: Path) -> Optional[Path]:
        """
        Determines the target category subfolder within the main destination directory
        for a given file, based on its extension.

        Files are ignored (and `None` is returned) if:
        1. The file has no extension.
        2. The file's extension is not present in the `EXTENSION_MAP`.

        If a valid category is found, the returned Path object will be of the form:
        `self.dest_dir / CategoryName` (e.g., "/path/to/dest_dir/Images").
        This method does not consider or replicate the original subdirectory
        structure from the source.

        Args:
            file_path: The `pathlib.Path` of the file being considered.

        Returns:
            A `pathlib.Path` object representing the full path to the target
            category subfolder, or `None` if the file should be ignored.
        """
        extension = file_path.suffix.lower() # Ensure lowercase for consistent map lookup

        if not extension:
            logger.debug(f"Ignoring file '{file_path.name}' (reason: no extension).")
            return None

        target_subfolder_name = self.session_extension_map.get(extension)

        if not target_subfolder_name:
            # This log now correctly reflects that the extension might be in the
            # session-specific map, which could include user-defined mapping or omissions.
            logger.debug(
                f"Ignoring file '{file_path.name}' (reason: extension '{extension}' "
                f"not in current session's extension map)."
            )
            return None

        return self.dest_dir / target_subfolder_name

    def _get_unique_destination_path(self, destination_folder: Path, original_file_name: str) -> Path:
        """
        Generates a unique file path within the `destination_folder` if a file
        with `original_file_name` already exists.

        Appends a numerical suffix (e.g., "(1)", "(2)") to the base name of the
        file until a non-existent path is found.

        Args:
            destination_folder: The `pathlib.Path` of the target category folder.
            original_file_name: The original name of the file (e.g., "document.pdf").

        Returns:
            A `pathlib.Path` object representing a unique path for the file
            within the `destination_folder`.
        """
        base_name = Path(original_file_name).stem
        extension = Path(original_file_name).suffix

        potential_dest_path = destination_folder / original_file_name
        counter = 1
        # Loop only if a file with the current potential name already exists
        while potential_dest_path.exists():
            # Safety break to prevent infinite loops in unexpected scenarios
            if counter > 1000:
                logger.error(
                    f"Could not find a unique name for {original_file_name} in "
                    f"{destination_folder} after 1000 attempts. "
                    f"Using original name, which may overwrite or fail."
                )
                return destination_folder / original_file_name # Fallback to original name

            new_name = f"{base_name}({counter}){extension}"
            potential_dest_path = destination_folder / new_name
            counter += 1
        return potential_dest_path

    def _move_file_with_deduplication(self, source_file_path: Path, destination_category_folder: Path) -> bool:
        """
        Moves a single file to its designated destination category folder,
        handling duplicates and creating the folder if necessary.

        Deduplication logic:
        - If a file with the same name exists at the destination:
            - Hashes of source and destination files are compared.
            - If hashes are identical: the source file is skipped (logged, not moved).
            - If hashes differ: the source file is renamed (e.g., "file(1).ext")
              using `_get_unique_destination_path` and then moved.
        - If no file with the same name exists: the source file is moved directly.

        Logs the action or simulates it if `self.dry_run` is True.

        Args:
            source_file_path: The `pathlib.Path` of the file to be moved.
            destination_category_folder: The `pathlib.Path` of the target category
                                         folder (e.g., ".../dest/Images").

        Returns:
            True if the file was processed (moved, renamed, or would be in dry_run),
            False if the file was skipped (e.g., identical duplicate found) or an
            error occurred during processing.
        """
        target_file_name = source_file_path.name
        # This is the initial path where the file would go if no conflict exists.
        prospective_dest_path = destination_category_folder / target_file_name

        if self.dry_run:
            if prospective_dest_path.exists():
                # In a real run, hashes would be compared here.
                logger.info(
                    f"[DRY RUN] File '{target_file_name}' already exists at '{destination_category_folder}'. "
                    f"Would compare hashes: if different, it would be renamed and moved; "
                    f"if same, it would be skipped."
                )
            else:
                logger.info(f"[DRY RUN] Would move '{source_file_path.name}' to '{prospective_dest_path}'")
            return True # In dry_run, all "considered" files are marked as processed for counting.

        # --- Real Movement Logic (not dry_run) ---
        final_dest_path_for_move = prospective_dest_path
        log_action_prefix = "Moving" # Default log prefix

        if prospective_dest_path.exists():
            logger.debug(f"File '{target_file_name}' already exists at '{destination_category_folder}'. Comparing hashes...")
            source_hash = self._calculate_file_hash(source_file_path)
            dest_hash = self._calculate_file_hash(prospective_dest_path)

            if source_hash is None:
                logger.error(f"Skipping '{source_file_path.name}' due to error calculating its hash.")
                return False
            if dest_hash is None:
                logger.error(
                    f"Skipping '{source_file_path.name}'. Could not calculate hash for "
                    f"existing destination file '{prospective_dest_path.name}'."
                )
                return False

            if source_hash == dest_hash:
                logger.info(
                    f"Skipping identical file (same name '{target_file_name}', same hash) "
                    f"Source: '{source_file_path}'. Destination: '{prospective_dest_path}'."
                )
                self.skipped_identical_duplicates += 1
                # Optionally, one could delete the source_file_path here if desired,
                # e.g., if source_file_path.exists(): source_file_path.unlink()
                return False # File was skipped, not moved/renamed.
            else: # Same name, different hashes.
                logger.info(
                    f"File '{target_file_name}' exists at '{destination_category_folder}' "
                    f"but with different content (hashes differ). Renaming source before move."
                )
                final_dest_path_for_move = self._get_unique_destination_path(destination_category_folder, target_file_name)
                if final_dest_path_for_move.name != target_file_name:
                    log_action_prefix = "Moving (renamed)"
        
        # At this point, either the destination path was clear, or it has been resolved to a unique name.
        logger.info(f"{log_action_prefix} '{source_file_path.name}' to '{final_dest_path_for_move}'")

        try:
            # Ensure the destination category folder (and any necessary parent folders) exists.
            destination_category_folder.mkdir(parents=True, exist_ok=True)
            # Perform the actual move operation.
            shutil.move(str(source_file_path), str(final_dest_path_for_move))
            logger.info(f"Successfully moved '{source_file_path.name}' to '{final_dest_path_for_move}'")
            self.files_successfully_moved_or_renamed += 1
            return True # File successfully moved or renamed.
        except shutil.Error as e: # Specific error from shutil operations
            logger.error(f"Shutil Error moving file '{source_file_path.name}' to '{final_dest_path_for_move}': {e}")
        except OSError as e: # Broader OS-level errors (permissions, disk full, etc.)
            logger.error(f"OS Error moving file '{source_file_path.name}' to '{final_dest_path_for_move}': {e}")
        except Exception as e: # Catch-all for other unexpected errors during the move
            logger.error(
                f"Unexpected error moving file '{source_file_path.name}' to '{final_dest_path_for_move}': {e}",
                exc_info=True # Include traceback information in the log
            )
        return False # Return False if any error occurred during the move.

    def organize(self) -> None:
        """
        Scans the source directory (and its subdirectories) recursively and
        organizes recognized files into the destination directory.

        For each file found:
        - Determines the appropriate destination category folder.
        - If a valid folder is found, attempts to move the file using
          `_move_file_with_deduplication`, which handles duplicate checks.
        - Updates internal counters for successfully moved/renamed files and
          skipped duplicates.
        Finally, logs a summary of the organization process.
        """
        logger.info(f"Starting recursive organization process for '{self.source_dir}'...")

        # --- NEW LOGIC TO DISCOVER EXTENSIONS ---
        logger.info(f"Scanning '{self.source_dir}' to discover all file extensions...")
        found_extensions = set() # Using set to store unique extensions

        for item_path_discovery in self.source_dir.rglob('*'): # Use a different variable name to avoid conflict
            if item_path_discovery.is_file():
                extension = item_path_discovery.suffix.lower() # Get extension in lowercase
                if extension: # Add only if the extension is not empty
                    found_extensions.add(extension)
        
        if found_extensions:
            logger.info(f"Discovered the following extensions in the source directory:") 
            # Sort the list of extensions for consistent and readable output
            for ext in sorted(list(found_extensions)):
                logger.info(f"  - {ext}")
        else:
            logger.info("No files with extensions found in the source directory.")
        # --- END OF NEW EXTENSION DISCOVERY LOGIC ---
            
        # --- INTERACTIVE MAPPING FOR UNMAPPED EXTENSIONS ---
        # We will use a copy of the global EXTENSION_MAP for this session,
        # so modifications don't affect other instances or future default runs
        # unless explicitly saved by the user later.
        # For now, let's assume self.extension_map will be this session's map.
        # In a more advanced version, self.extension_map might be loaded from user config in __init__.
        
        # Create a working copy of the extension map for this session
        # This allows modifications without altering the global EXTENSION_MAP directly
        # or affecting other FileOrganizer instances if this class were used differently.
        # For simplicity now, we'll directly use EXTENSION_MAP and potentially modify a copy later.
        # Let's define what the "current" map is for this session.
        # For now, we'll build up `session_specific_mappings` and then decide how to merge/use it.
        
        current_default_mapped_extensions = set(self.session_extension_map.keys())
        unmapped_extensions = found_extensions - current_default_mapped_extensions

        # This dictionary will hold new mapping defined by user in this sessions.
        newly_mapped_by_user = {}

        if unmapped_extensions:
            logger.info("---------------------------------------------------------------------")
            logger.info("Interactive Extension Mapping:")
            logger.info("The following discovered extensions are not in the default map:")
            for ext in sorted(list(unmapped_extensions)):
                logger.info(f"  - {ext}")
            
            logger.info("You will now be prompted to assign a destination folder for each.")
            logger.info("Pressing ENTER without typing a folder name will ignore the extension for this session.")
            logger.info("---------------------------------------------------------------------")

            for ext in sorted(list(unmapped_extensions)):
                while True:
                    prompt_message = (
                        f"For extension '{ext}': Enter target folder name "
                        f"(e.g., MyCustomFiles) or leave blank to IGNORE: "
                    )
                    try:
                        user_folder_name = input(prompt_message).strip()
                    except EOFError: # Handle if input stream is closed (e.g., piping)
                        logger.warning(f"EOF encountered. Ignoring remaining unmapped extensions.")
                        user_folder_name = "" # Treat as ignore
                        unmapped_extensions = set() # Clear remaining to stop loop
                        break

                    if not user_folder_name:
                        logger.info(f"  -> Extension '{ext}' will be IGNORED for this session.")
                        break

                    # Basic validation for folder names (can be expanded)
                    # For simplicity, we'll just check for obviously problematic characters.
                    # A more robust solution would check against OS-specific invalid characters.
                    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
                    if any(char in user_folder_name for char in invalid_chars) or \
                       user_folder_name.startswith('.') or user_folder_name.endswith('.') or \
                       user_folder_name.endswith(' '):
                        logger.warning(
                            f"  -> Invalid folder name: '{user_folder_name}'. "
                            f"Please use valid characters and avoid slashes, leading/trailing dots or spaces."
                        )
                        continue # Ask again for the same extension

                    logger.info(f"  -> Extension '{ext}' will be organized into folder: '{user_folder_name}'")
                    self.session_extension_map[ext] = user_folder_name
                    newly_mapped_by_user[ext] = user_folder_name
                    break

            if newly_mapped_by_user:
                logger.info("---------------------------------------------------------------------")
                logger.info("Summary of new mapping for this session:")
                for ext, folder in newly_mapped_by_user.items():
                    logger.info(f"  '{ext}' will go to '{folder}'")
                logger.info("---------------------------------------------------------------------")
        
        else: # No unmapped extensions found
            logger.info("All discovered extensions are already covered by the current session's mappings.")
        # --- END OF INTERACTIVE MAPPING LOGIC ---

        # --- Actual Organization Pass (using the potentially updated self.session_extension_map) ---
        logger.info("Proceeding with file organization...")
        total_files_scanned = 0
        files_considered_for_processing = 0 # Files that pass the extension filter
        files_ignored_by_rule = 0           # Files ignored due to no/unmapped extension

        # Reset counters for this organization run (if the instance is reused)
        self.files_successfully_moved_or_renamed = 0
        self.skipped_identical_duplicates = 0

        # `Path.rglob('*')` recursively finds all files and directories.
        # This loop is for the actual processing and moving of files.
        for item_path in self.source_dir.rglob('*'):
            if item_path.is_file():
                total_files_scanned += 1
                # Use DEBUG for per-file scanning during organization pass if -v is used
                logger.debug(f"Processing file: '{item_path}'") 

                # We are modifying _get_destination_folder_or_ignore to use self.session_extension_map

                destination_category_folder = self._get_destination_folder_or_ignore(item_path)

                if destination_category_folder is None:
                    files_ignored_by_rule += 1
                    continue

                files_considered_for_processing += 1
                self._move_file_with_deduplication(item_path, destination_category_folder)
            
            elif item_path.is_dir():
                logger.debug(f"Scanning within directory (organization pass): '{item_path}'.")
            else:
                logger.warning(f"Skipping item that if not a file or directory: '{item_path}'")
                
        # --- Log Summary ---
        log_summary_prefix = "Dry run finished." if self.dry_run else "Organization finished."
        logger.info(f"--- {log_summary_prefix} ---")
        logger.info(f"Total files scanned (during organization pass): {total_files_scanned}")
        logger.info(f"Files ignored by (default or session) extension rules: {files_ignored_by_rule}")

        if self.dry_run:
            logger.info(f"Files that would be considered for moving/renaming: {files_considered_for_processing}")
            logger.info(f"   (In dry run, duplicate checks and renaming are simulated and logged per file.)")
        else:
            logger.info(f"Files successfully moved or renamed: {self.files_successfully_moved_or_renamed}")
            logger.info(f"Identical duplicate files skipped: {self.skipped_identical_duplicates}")
        
        # Calculate files that were considered but not accounted for by successful moves or skips
        # (e.g., due to hash calculation errors or move errors).
        unaccounted_for = files_considered_for_processing - (self.files_successfully_moved_or_renamed + self.skipped_identical_duplicates)
        if not self.dry_run and unaccounted_for > 0:
            logger.info(f"Files considered but not moved/skipped (e.g., due to errors): {unaccounted_for}")

def main() -> None:
    """
    Main function to parse command-line arguments, initialize the FileOrganizer,
    and start the organization process.
    Handles exceptions during setup and execution.
    """
    parser = argparse.ArgumentParser(
        description="Organizes files from a source directory (recursively) into "
                    "categorized subdirectories within a destination directory "
                    "based on file extension, handling duplicates."
    )
    parser.add_argument(
        "source_dir",
        type=Path,
        help="The source directory containing files to organize."
    )
    parser.add_argument(
        "dest_dir",
        type=Path,
        help="The base destination directory where organized sub-folders will be created."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulates the organization process without actually moving files. "
             "Logs intended actions instead."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO, # Default log level if -v is not specified
        help="Increase output verbosity to DEBUG level."
    )

    args = parser.parse_args()

    # Set the logging level for the root logger and this module's logger.
    # This ensures that the verbosity flag applies correctly.
    logging.getLogger().setLevel(args.loglevel) # Affects root logger, and subsequently all others
    logger.setLevel(args.loglevel)             # Explicitly set for this module's logger

    try:
        organizer = FileOrganizer(args.source_dir, args.dest_dir, args.dry_run)
        organizer.organize()
        logger.info("Organization process completed successfully.")
    except ValueError as e: # Catches validation errors from FileOrganizer.__init__
        logger.critical(f"Configuration Error: {e}")
        sys.exit(1) # Exit with a non-zero status code to indicate failure
    except Exception as e: # Catch any other unexpected critical errors
        logger.critical(f"An unexpected critical error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
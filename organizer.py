import argparse
import logging
import sys
import shutil
from pathlib import Path # To manipulate paths and files
import hashlib
from typing import Optional, Dict
import json
from platformdirs import user_config_dir

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

# --- Constants ---
APP_NAME = "File Organizer - CLI Version"
APP_AUTHOR = "Giselly Oliveira"
CONFIG_FILE_NAME = "extension_map_config.json"

# --- Extension to Folder Mapping ---
# This dictionary defines how files are categorized based on their extensions.
# Only files with extensions present in this map will be processed by the organizer.
# Keys are file extensions (lowercase, with a leading dot).
# Values are the names of the subfolders to be created in the destination directory.
DEFAULT_EXTENSION_MAP = {
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

        self.config_path = self._get_config_file_path()
        self.session_extension_map = self._load_extension_map_config()
        # Flag to track if the map was changed during the session
        self._map_changed_this_session = False

        logger.info(
            f"Organizer initialized. Source: '{self.source_dir}', "
            f"Destination: '{self.dest_dir}', Dry Run: {self.dry_run}"
        )
        logger.info(f"Using configuration from: {self.config_path}")
    

    def _get_config_file_path(self) -> Path:
        """Determines the path for the configuration file.""" 
        # uses platformdirs to find an appropriate user-specific config directory
        config_dir = Path(user_config_dir(APP_NAME, APP_AUTHOR, roaming=True))
        config_dir.mkdir(parents=True, exist_ok=True) # Ensure the directory exists
        return config_dir / CONFIG_FILE_NAME
    

    def _load_extension_map_config(self) -> Dict[str, str]:
        """Loads the extension map from the user's config file, or returns defaults."""
        if self.config_path.exists() and self.config_path.is_file():
            try:
                with self.config_path.open('r', encoding='utf-8') as f:
                    user_map = json.load(f)
                # Basic validation: check if it's a dictionary
                if isinstance(user_map, dict):
                    logger.info(f"Loaded custom extension map from {self.config_path}")
                    # Merge with defaults, user_map takes precedence for existing keys
                    # and adds new keys.
                    # Starts with a copy of defaults, then update.
                    # This ensures any new defaults added to the script are available
                    # if not overridden by the user.
                    combined_map = DEFAULT_EXTENSION_MAP.copy()
                    combined_map.update(user_map)
                    return combined_map
                else:
                    logger.warning(
                        f"Configuration file {self.config_path} is not a valid JSON dictionary. "
                        f"Using default extension map."
                    )
            except json.JSONDecodeError:
                logger.warning(
                    f"Error decoding JSON from {self.config_path}. "
                    f"Using default extension map."
                    )
            except Exception as e:
                logger.error(
                    f"Unexpected error loading config from {self.config_path}: {e}. "
                    f"Using default extension map.", exc_info=True
                ) 
        else:
            logger.info("No custom configuration file found. Using default extension map.")
        return DEFAULT_EXTENSION_MAP.copy() # Return a copy of defaults


    def _interactive_edit_existing_mappings(self) -> None:
        """ 
        Allows the user to interactively review and modify existing extension mappings
        in the current session's map (self.session_extension_map).
        Sets self._map_changed_this_session to True if any changes are made.
        """
        try:
            review_choice = input("Review or modify current extension mappings? (yes/No, default: No): ").strip().lower()
            # Get the first character if input is not empty, otherwise default to 'n' (for No)
            first_char_review_choice = review_choice[0] if review_choice else 'n'
        except EOFError:
            logger.warning("\nInput stream closed (EOF). Skipping review of existing mappings.")
            return
        
        if first_char_review_choice != 'y':
            logger.info("Skipping review of existing mappings.")
            return
        
        logger.info("---------------------------------------------------------------------")
        logger.info("Review/Modify Existing Extension Mappings:")
        
        if not self.session_extension_map:
            logger.info("  No mappings currently defined.")
        else:
            logger.info("Current mappings (extension -> destination folder):")
            for ext, folder in sorted(self.session_extension_map.items()):
                logger.info(f"  '{ext}' -> '{folder}'")
        logger.info("---------------------------------------------------------------------")

        while True:
            try:
                ext_to_modify_input = input("Enter extension to modify (e.g., .pdf), or type 'done' to finish: ").strip().lower()
            except EOFError:
                logger.warning("\nInput stream closed (EOF). Exiting modification mode.")
                break

            if ext_to_modify_input == 'done':
                break

            if not ext_to_modify_input.startswith('.') or len(ext_to_modify_input) < 2: # Basic validation for extension format
                if ext_to_modify_input: # Only warn if it's not an empty string (which means 'exit' was intended)
                    logger.warning(f"  Invalid extension format: '{ext_to_modify_input}'. Must start with a dot and have characters after it(e.g., .txt).")
                continue

            if ext_to_modify_input in self.session_extension_map:
                current_folder = self.session_extension_map[ext_to_modify_input]
                prompt_message = (
                    f"  Extension '{ext_to_modify_input}' currently maps to '{current_folder}'.\n"
                    f"  New folder (Enter to keep, type 'ignore' to remove mapping, or new folder name): "
                )
                try:
                    new_folder_name = input(prompt_message).strip()
                except EOFError:
                    logger.warning("\nInput stream closed (EOF). Cancelling modification for this extension.")
                    continue 

                if not new_folder_name: # User pressed Enter, keep current
                    logger.info(f"  Mapping for '{ext_to_modify_input}' remains '{current_folder}'.")
                
                elif new_folder_name.lower() == 'ignore':
                    del self.session_extension_map[ext_to_modify_input]
                    self._map_changed_this_session = True
                    logger.info(f"  Mapping for '{ext_to_modify_input}' removed for this session.")

                else: # Should not happen if ext_to_modify_input was in session_extension_map
                    # Validate new_folder_name (similar to the other interactive part)
                    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
                    if any(char in new_folder_name for char in invalid_chars) or \
                        new_folder_name.startswith('.') or new_folder_name.endswith('.') or \
                        new_folder_name.endswith(' '):
                            logger.warning(
                                f"  -> Invalid folder name: '{new_folder_name}'. "
                                f"Please use valid characters and avoid slashes, leading/trailing dots or spaces."
                            )
                    else:
                        if current_folder != new_folder_name:
                            self.session_extension_map[ext_to_modify_input] = new_folder_name
                            self._map_changed_this_session = True
                            logger.info(f"  Mapping for '{ext_to_modify_input}' changed from '{current_folder}' to '{new_folder_name}'.")
                        else:
                            logger.info(f"  Mapping for '{ext_to_modify_input}' remains '{current_folder}' (no change).")
            else:
                logger.info(f"  Extension '{ext_to_modify_input}' not found in current mappings. You can add it when prompted for unmapped extensions.")
                
        logger.info("Finished reviewing/modifying existing mappings.")
        logger.info("---------------------------------------------------------------------")


    def _save_extension_map_config(self) -> None:
        """Saves the current session_extension_map to the user's config file."""
        # it checks if there were no changes. If so, report and exit (regardless of dry_run).
        if not self._map_changed_this_session:
            logger.info("No changes made to extension mappings this session. Nothing to save.")
            return
        
        # If there were changes, check if it is dry_run. If so, report and exit.
        if self.dry_run:
            logger.info("Dry run: Configuration changes will not be saved.")
            return
        
        # If there have been changes AND it is NOT dry_run, then ask the user.
        try:
            save_choice = input("Save current extension mappings for future use? (yes/No): ").strip().lower()
            # Get the first character if input is not empty, otherwise default to 'n' (for No)
            first_char_save_choice = save_choice[0] if save_choice else 'n'
                
            if first_char_save_choice == 'y':
                with self.config_path.open('w', encoding='utf-8') as f:
                        json.dump(self.session_extension_map, f, indent=4, sort_keys=True)
                logger.info(f"Extension mappings saved to {self.config_path}")
            else:
                logger.info(f"Extension mappings not saved for this session.")
        except EOFError:
            logger.warning("Input stream closed (EOF). Mappings not saved.")
        except Exception as e:
            logger.error(f"Error saving configuration to {self.config_path}: {e}", exc_info=True)


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
        Scans the source directory, allows interactive review/modification of existing
        extension mappings, prompts for unmapped extensions, organizes files accordingly,
        and optionally saves updated mappings.

        The process involves:
        1. Discovering all unique file extensions in the source directory.
        2. Optionally allowing the user to review and modify current extension mappings.
        3. Identifying any remaining extensions not present in the (potentially modified)
           `self.session_extension_map`.
        4. Prompting the user to define destination folders for these newly unmapped extensions.
           These new mappings are added to `self.session_extension_map`.
        5. Iterating through all files for the actual organization using the final
           `self.session_extension_map`.
        6. Logging a summary and prompting to save configuration if changes were made.
        """
        logger.info(f"Starting interactive organization process for '{self.source_dir}'...")
        # Reset flag at the start of organization. It will be set to True if any
        # existing mapping is changed or any new mapping for an unmapped extension is added.
        self._map_changed_this_session = False 

        # --- DISCOVER ALL EXTENSIONS IN SOURCE DIRECTORY ---
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
            logger.info("No files with extensions found in the source directory. Nothing to organize based on extensions.")
            
        # --- INTERACTIVELY REVIEW/MODIFY EXISTING MAPPINGS ---
        # This method will modify self.session_extension_map directly and set self._map_changed_this_session
        self._interactive_edit_existing_mappings() # User can modify defaults or loaded config here

        # --- INTERACTIVE MAPPING FOR NEWLY UNMAPPED EXTENSIONS ---
        # Recalculate unmapped_extensions based on the potentially modified self.session_extension_map
        current_mapped_extensions_in_session = set(self.session_extension_map.keys())
        unmapped_extensions = found_extensions - current_mapped_extensions_in_session

        if unmapped_extensions:
            logger.info("Interactive Mapping for Newly Discovered/Unmapped Extensions:")
            logger.info("The following discovered extensions are not in the current mappings:")
            for ext in sorted(list(unmapped_extensions)):
                logger.info(f"  - {ext}")
            
            logger.info("You will now be prompted to assign a destination folder for each.")
            logger.info("Pressing ENTER (leaving blank) will ignore the extension for this session.")
            logger.info("---------------------------------------------------------------------")

            for ext in sorted(list(unmapped_extensions)): # Iterate again, in case some were handled by editing existing
                while True:
                    prompt_message = (
                        f"For extension '{ext}': Enter target folder name "
                        f"(e.g., MyCustomFiles) or leave blank to IGNORE: "
                    )
                    try:
                        user_folder_name = input(prompt_message).strip()
                    except EOFError: # Handle if input stream is closed (e.g., piping)
                        logger.warning(f"\nInput stream closed (EOF). Ignoring remaining unmapped extensions.")
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
                    
                    # If input is valid and not empty, map it.
                    logger.info(f"  -> Extension '{ext}' will be organized into folder: '{user_folder_name}'")
                    self.session_extension_map[ext] = user_folder_name
                    self._map_changed_this_session = True # A mapping was added/changed
                    break

            if self._map_changed_this_session: # Check if any changes were made in either interactive step
                logger.info("---------------------------------------------------------------------")
                logger.info("Session mappings have been updated based on your input.")
                logger.info("---------------------------------------------------------------------")
        
        elif not found_extensions: # This case was handled by the first block, but good to be explicit
            pass # No extension found, no unmapped extensions. 
        
        else: # All found extensions were already in the (potentially user-modified) session_extension_map
            logger.info("All discovered extensions are already covered by the current session's mappings.")
        # --- END OF INTERACTIVE MAPPING FOR UNMAPPED EXTENSIONS ---

        # --- Actual Organization Pass ---
        logger.info("Proceeding with file organization using current session mappings...")
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
        
        # --- SAVE CONFIGURATION (if not dry_run and changes were made) ---
        self._save_extension_map_config()
        # ---  END OF SAVE CONFIGURATION ---


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
    
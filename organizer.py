import argparse
import logging
import sys
import shutil 
from pathlib import Path # Manipulates paths/files
import hashlib
from typing import Optional


# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout) # Log to console
    ]
)
logger = logging.getLogger(__name__)


# --- Basic Mapping of Extensions to Folders ---
# Only files with extensions in this map will be processed.
EXTENSION_MAP = {
    '.txt': "TextFiles",
    '.pdf': "Documents",
    '.docx': "Documents",
    '.doc': "Documents",
    '.odt': "Documents",      
    '.rtf': "Documents",      
    '.epub': "Ebooks",        
    '.mobi': "Ebooks",        
    '.xlsx': "Spreadsheets",
    '.xls': "Spreadsheets",   
    '.ods': "Spreadsheets",   
    '.csv': "Data", 
    '.jpg': "Images",
    '.jpeg': "Images",
    '.png': "Images",
    '.gif': "Images",
    '.bmp': "Images",         
    '.tiff': "Images",        
    '.webp': "Images",        
    '.heic': "Images",        
    '.svg': "VectorGraphics", 
    '.psd': "Design_Files",   
    '.ai': "Design_Files",
    '.zip': "Archives",
    '.rar': "Archives",
    '.tar': "Archives",       
    '.gz': "Archives",       
    '.7z': "Archives", 
    '.exe': "Executables_Installers", 
    '.msi': "Executables_Installers", 
    '.dmg': "Executables_Installers", 
    '.pkg': "Executables_Installers", 
    '.deb': "Executables_Installers", 
    '.rpm': "Executables_Installers", 
    '.jar': "Executables_Installers",
    '.mp3': "Music",
    '.wav': "Audio",          
    '.aac': "Audio",          
    '.flac': "Audio",         
    '.ogg': "Audio",          
    '.m4a': "Audio", 
    '.mp4': "Videos",
    '.avi': "Videos",
    '.mkv': "Videos",
    '.mov': "Videos",         
    '.wmv': "Videos",         
    '.flv': "Videos",             
    '.log': "LogFiles",       
    '.json': "Data",          
    '.xml': "Data",           
    '.yaml': "Configs",       
    '.yml': "Configs",        
    '.ttf': "Fonts",         
    '.otf': "Fonts",      
}


# --- Organizer Main Class ---
class FileOrganizer:
    """
    Sorts files from a source directory (and its sub-folders) into categorized
    sub-folders within a destination directory. Only processes files with recognized
    extensions (defined in EXTENSION_MAP). Files are copied, and the original
    directory structure is replicated within the category folders.
    """
    def __init__(self, source_dir: Path, dest_dir: Path, dry_run: bool = False):
        """
        Initializes the organizer.

        Args:
            source_dir (Path): The directory where the files to be organized are located.
            dest_dir (Path): The base directory where the destination sub-folders will be created.
            dry_run (bool): If True, just simulates the actions and logs, without moving files.
        """
        if not source_dir.is_dir():
            raise ValueError(f"Source directory does not exists or is not a directory: {source_dir}")
        if dest_dir.exists() and not dest_dir.is_dir():
            raise ValueError(f"Destination path exists but is not a directory: {dest_dir}")
        
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.dry_run = dry_run
        self.files_successfully_moved_or_renamed = 0
        self.skipped_identical_duplicates = 0
        logger.info(f"Organizer initialized. Source: '{self.source_dir}', Destination: '{self.dest_dir}', Dry Run: {self.dry_run}")
    

    def _calculate_file_hash(self, file_path: Path, hash_algo: str = "sha256", buffer_size: int = 65536) -> Optional[str]:
        """ 
        Calculates the hash of a file.

        Args:
            file_path (Path): The path to the file.
            hash_algo (str): The hashing algorithm to use (e.g., "md5", "sha256").
            buffer_size (int): The size of chunks to read from the file.

        Returns:
            Optional[str]: The hexadecimal hash string, or None if an error occurs.
        """
        hasher = hashlib.new(hash_algo)
        try:
            with open(file_path, 'rb') as f:
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
        except Exception as e:
            logger.error(f"Hash calculation: Unexpected error for file {file_path}: {e}", exc_info=True)
            return None


    def _get_destination_folder_or_ignore(self, file_path: Path) -> Optional[Path]:
        """
        Determines the destination folder for a file based on its extension.
        Returns None if the file should be ignored based on:
        1. No extension.
        2. Extension not in EXTENSION_MAP.

        Args:
            file_path (Path): The path to the file.

        Returns:
            Optional[Path]: The full path to the destination sub-folder, or None if the file should be ignored.
    """
        extension = file_path.suffix.lower() # Get the extension in lowercase (ex: '.pdf')
        
        if not extension:
            logger.debug(f"Ignoring file '{file_path.name}' (reason: no extension).")
            return None 
        
        # If the extension is not in the map, .get() will return None, and the file will be ignored.
        target_subfolder_name = EXTENSION_MAP.get(extension) # Gets the folder name from MAP
        
        if not target_subfolder_name:
            logger.debug(f"Ignoring file '{file_path.name}' (reason: extension '{extension}' not in EXTENSION_MAP).")
            return None
        
        return self.dest_dir / target_subfolder_name
    

    def _get_unique_destination_path(self, destination_folder: Path, original_file_name: str) -> Path:
        """ 
        Generates a unique file path in the destination folder if a file with the
        original_file_name already exists. Appends (1), (2), etc.

        Args:
            destination_folder (Path): The target folder.
            original_file_name (str): The original name of the file (e.g., "document.pdf").

        Returns:
            Path: A unique path in the destination folder for the file.
        """
        base_name = Path(original_file_name).stem
        extension = Path(original_file_name).suffix

        potential_dest_path = destination_folder / original_file_name
        counter = 1
        while potential_dest_path.exists(): # Loop only is the file name already exists
            new_name = f"{base_name}({counter}){extension}"
            potential_dest_path = destination_folder / new_name
            counter += 1
            if counter > 1000: # Safe mode to avoid infinite loop
                logger.error(f"Could not find a unique name for {original_file_name} in {destination_folder} after 1000 attempts. Skipping...")
                return potential_dest_path
            return potential_dest_path


    def _move_file_with_deduplication(self, source_file_path: Path, destination_folder: Path) -> bool:
        """
        Moves a single file to the designated destination folder,
        creating the folder if necessary. Handles duplicates:
        - If same name & same hash: skips moving the source file.
        - If same name & different hash: renames the source file before moving.
        Logs the action or simulates if dry_run=True.

        Args:
            source_file_path (Path): The path of the file to be moved.
            destination_folder (Path): The destination folder to move to.

        Returns:
            bool: True if the file was processed (moved, renamed, or would be in dry_run),
                  False if skipped (e.g., identical duplicate) or an error occurred.
        """
        target_file_name = source_file_path.name
        prospective_dest_path = destination_folder / target_file_name 

        # --- Dry Run Here ---
        if self.dry_run:
            if prospective_dest_path.exists():
                logger.info(f"[DRY RUN] File '{target_file_name}' already exists at '{destination_folder}'. "
                            f"Would compare hashes: if different, it would be renamed and moved; "
                            f"if same, it would be skipped.")
            else:
                logger.info(f"[DRY RUN] Would move '{source_file_path.name}' to '{prospective_dest_path}'")
            return True # In dry_run, we consider the file to have been "processed" for counting purposes.
        
        # --- Real Movement Here ---
        final_dest_path_for_move = prospective_dest_path
        log_action_prefix = "Moving"

        if prospective_dest_path.exists():
            # Name conflict! We need to check the hashes.
            logger.debug(f"File '{target_file_name}' already exists at '{destination_folder}'. Comparing hashes...")
            source_hash = self._calculate_file_hash(source_file_path)
            dest_hash = self._calculate_file_hash(prospective_dest_path)

            if source_hash is None:
                logger.error(f"Skipping '{source_file_path.name}' due to error calculating its hash.")
                return False
            if dest_hash is None:
                # If we can't compute the hash of the destination, it's risky to assume.
                # It could be a temporary or corrupt file.
                # To be safe, we will skip the move to avoid overwriting something unexpected.
                logger.error(f"Skipping '{source_file_path.name}'. Could not calculate hash for existing destination file '{prospective_dest_path.name}'.")
                return False
            
            if source_hash == dest_hash:
                logger.info(f"Skipping identical file (same name '{target_file_name}', same hash) "
                            f"Source: '{source_file_path}'. Destination: '{prospective_dest_path}'.")
                self.skipped_identical_duplicates += 1 
                # Opcional: deletar o source_file_path aqui se desejado e não for dry_run
                # if source_file_path.exists(): source_file_path.unlink()
                return False # Returns False because the file was skipped (not moved)
            else:
                # Same names, different hashes. We need to rename the source file before moving.
                logger.info(f"File '{target_file_name}' exists at '{destination_folder}' but with different content (hashes differ). Renaming source before move.")
                final_dest_path_for_move = self._get_unique_destination_path(destination_folder, target_file_name)
                log_action_prefix = "Moving (renamed)"
        
        # If it got here, either the destination didn't exist, or it was renamed to a unique path.
        logger.info(f"{log_action_prefix} '{source_file_path.name}' to '{final_dest_path_for_move}'")

        try:
            # Creates the destination folder and any necessary parent folders
            destination_folder.mkdir(parents=True, exist_ok=True)
            # Moves the file
            shutil.move(str(source_file_path), str(final_dest_path_for_move))
            logger.info(f"Successfully moved '{source_file_path.name}' to '{final_dest_path_for_move}'")
            self.files_successfully_moved_or_renamed += 1
            return True # Successfully moved.
        except OSError as e:
            logger.error(f"OS Error moving files '{source_file_path.name}' to '{final_dest_path_for_move}': {e}")
        except shutil.Error as e:
            logger.error(f"Shutil Error moving file '{source_file_path.name}' to '{final_dest_path_for_move}': {e}")
        except Exception as e:
              # Generic catch for other unexpected errors
            logger.error(f"Unexpected error moving file '{source_file_path.name}' to {final_dest_path_for_move}': {e}", 
                         exc_info=True) # exc_info=True adds traceback to log
            return False # Failed to move


    def organize(self) -> None:
        """
        Scans the source directory and its subdirectories recursively.
        Copies files with recognized extensions to categorized folders in the destination,
        replicating the source's subdirectory structure.
        """
        logger.info(f"Starting recursive organization process for '{self.source_dir}'...")
        
        total_files_scanned = 0
        files_considered_for_processing = 0 # Files that passed the extension filter
        files_ignored_by_rule = 0 # Files ignored due to no extension or unmapped extension

        # Reset counters for each organize call (if instance is reused)
        self.files_successfully_moved_or_renamed = 0
        self.skipped_identical_duplicates = 0

        # ALTERAÇÃO: Iterar recursivamente sobre todos os itens no diretório de origem
        # self.source_dir.rglob('*') encontra todos os arquivos e diretórios recursivamente.
        for item_path in self.source_dir.rglob('*'):
            if item_path.is_file(): # process files only
                total_files_scanned += 1
                logger.debug(f"Scanning file: '{item_path}'")

                # Determines where the file should go, or None if it should be ignored by extension rules
                destination_folder = self._get_destination_folder_or_ignore(item_path)

                if destination_folder is None:
                    # File was ignored by extension rule (no extension or not mapped in EXTENSION_MAP)
                    files_ignored_by_rule += 1
                    # Specific logging of the ignore reason has already been done in _get_destination_folder_or_ignore
                    continue

                # If it got here, the file passed the extension filter and has a destination.
                files_considered_for_processing += 1

                # Attempts to move the file (or simulates) and handles duplicates
                # Counting of moves/renamed and identical duplicates is done inside _move_file_with_deduplication
                self._move_file_with_deduplication(item_path, destination_folder)
            
            elif item_path.is_dir():
                # We don't need to do anything for directories here, rglob already takes care of the recursion.
                logger.debug(f"Scanning within directory: '{item_path}'.")
            else:
                logger.warning(f"Skipping item that is not a file or directory: '{item_path}'")

        # --- Log Summary ---
        log_summary_prefix = "Dry run finished." if self.dry_run else "Organization finished."
        logger.info(f"--- {log_summary_prefix} ---")
        logger.info(f"Total files scanned: {total_files_scanned}")
        logger.info(f"Files ignored by extension rules: {files_ignored_by_rule}")

        if self.dry_run:
            # In dry_run, files_considered_for_processing is the number of files that would be attempted.
            # Duplicate simulation is logged individually.
            logger.info(f"Files that would be considered for moving/renaming (passed extension filter): {files_considered_for_processing}")
            logger.info(f"   (In dry run, detailed dplicate checks and renaming are simulated and logged per file.)")
        else:
            logger.info(f"Files successfully moved or renamed: {self.files_successfully_moved_or_renamed}")
            logger.info(f"Identical duplicate files skipped: {self.skipped_identical_duplicates}")
        
        unaccounted_for = files_considered_for_processing - (self.files_successfully_moved_or_renamed + self.skipped_identical_duplicates)
        if not self.dry_run and unaccounted_for > 0:
            logger.info(f"Files considered but not moved/skipped: {unaccounted_for}")


    # --- Main Function and Arguments ---
def main() -> None:
    """
    Sets arguments, creates the organizer and starts the process.
    """
    parser = argparse.ArgumentParser(
        description="Organizes files from a source directory (recursively) into subdirectories "
                    "within a destination directory based on file extension, handling duplicates.")
    parser.add_argument("source_dir", 
                        type=Path, # Uses pathlib.Path to convert the argument
                        help="The source directory containing files to organize.")
    parser.add_argument("dest_dir", 
                        type=Path, 
                        help="The base destination where organized sub-folders will be created.")
    parser.add_argument("--dry-run", 
                        action="store_true", 
                        help="Simulates the organization process without actually copying files.")
    # Argument for log level
    parser.add_argument(
        "-v", "--verbose", 
        action="store_const", 
        dest="loglevel", 
        const=logging.DEBUG, 
        default=logging.INFO, 
        help="Increase output verbosity to DEBUG level."
        )
        
    args = parser.parse_args()

    logger.setLevel(args.loglevel)

    try:
        # Creates the organizer instance with the parsed arguments
        organizer = FileOrganizer(args.source_dir, args.dest_dir, args.dry_run)
        # Start the organization process
        organizer.organize()
        logger.info("Organization process completed.")
    except ValueError as e:
        # Catches __init__ validation errors (e.g. directory does not exist)
        logger.critical(f"Configuration Error: {e}") # Critical indicates fatal error
        sys.exit(1) # Leaves with error code
    except Exception as e:
        # Catches other unexpected errors during startup or setup
        logger.critical(f"An unexpected critical error ocurred: {e}", exc_info=True)
        sys.exit(1)


# --- Script Input Point ---
if __name__ == "__main__":
    main()
            
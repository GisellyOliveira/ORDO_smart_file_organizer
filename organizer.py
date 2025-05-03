import argparse
import logging
import sys
import shutil # Moves files more robustly
from pathlib import Path # Manipulates paths/files
from collections import defaultdict # Groups by extension


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
EXTENSION_MAP = defaultdict(lambda: "Others") # Default value if extension not found
EXTENSION_MAP.update({
    '.txt': "TextFiles",
    '.pdf': "Documents",
    '.docx': "Documents",
    '.xlsx': "Spreadsheets",
    '.jpg': "Images",
    '.jpeg': "Images",
    '.png': "Images",
    '.gif': "Images",
    '.zip': "Archives",
    '.rar': "Archives",
    '.exe': "Executables",
    '.msi': "Executables",
    '.mp3': "Music",
    '.wav': "Music",
    '.mp4': "Videos",
    '.avi': "Videos",
    '.mkv': "Videos",
})


# --- Organizer Main Class ---
class FileOrganizer:
    """
    Sorts files in a source folder into subfolders in a destination,
    based on rules (initially, file extension).
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
        logger.info(f"Organizer initialized. Source: '{self.source_dir}', Destination: '{self.dest_dir}', Dry Run: {self.dry_run}")
    

    def _get_destination_folder(self, file_path: Path) -> Path:
        """
        Determines the destination folder for a file based on its extension.

        Args:
            file_path (Path): The path to the file.

        Returns:
            Path: The full path to the destination folder where the file should go.
    """
        extension = file_path.suffix.lower() # Get the extension in lowercase (ex: '.pdf')
        if not extension:
            target_subfolder = "NoExtension"
        else:
            target_subfolder = EXTENSION_MAP[extension]
        return self.dest_dir / target_subfolder


    def _move_file(self, file_path: Path, destination_folder: Path) -> None:
        """
        Moves a single file to the designated destination folder,
        creating the folder if necessary. Logs the action or simulates if dry_run=True.

        Args:
            file_path (Path): The path of the file to be moved.
            destination_folder (Path): The destination folder to move to.
        """
        destination_path = destination_folder / file_path.name # Full path of the file in the destination


        log_prefix = "[DRY RUN] Would move" if self.dry_run else "Moving"
        logger.info(f"{log_prefix} '{file_path.name}' to '{destination_folder}'")

        if not self.dry_run:
            try:
                # Creates the destination folder and any necessary parent folders
                # exist_ok=True avoids error if folder already exists
                destination_folder.mkdir(parents=True, exist_ok=True)

                # Moves the file
                shutil.move(str(file_path), str(destination_path)) 
                logger.info(f"Successfully moved '{file_path.name}'")
            
            except OSError as e:
                logger.error(f"OS Error moving file '{file_path.name}': {e}")
            except shutil.Error as e:
                logger.error(f"Shutil Error moving file '{file_path.name}': {e}")
            except Exception as e:
                # Generic catch for other unexpected errors
                logger.error(f"Unexpected error moving file '{file_path.name}': {e}", 
                             exc_info=True) # exc_info=True adds traceback to log


    def organize(self) -> None:
        """
        Scans the source directory and organizes the found files.
        """
        logger.info(f"Starting organization process for '{self.source_dir}'...")
        file_count = 0
        moved_count = 0

        # Iterate over the items in the source directory
        for item in self.source_dir.iterdir(): # It ignores subdirectories for now
            if item.is_file():
                file_count += 1
                logger.debug(f"Processing file: '{item.name}'")

                # Determines where the file should go
                destination_folder = self._get_destination_folder(item) 
                # Moves (or simulates moving) the file
                self._move_file(item, destination_folder)
                # Increment counter (even in dry-run to know what would be moved)
                moved_count += 1
            elif item.is_dir():
                logger.debug(f"Skipping directory: '{item.name}'")
            else:
                logger.warning(f"Skipping item that is not a file or directory: '{item.name}'")
        
        log_summary_prefix = "Dry run finished." if self.dry_run else "Organization finished."
        log_action = "would be moved" if self.dry_run else "processed/moved"
        logger.info(f"{log_summary_prefix} Found {file_count} files. {moved_count} files {log_action}.")
    

    # --- Main Function and Arguments ---
def main() -> None:
    """
    Sets arguments, creates the organizer and starts the process.
    """
    parser = argparse.ArgumentParser(
        description="Organizes files from a source directory into subdirectories within a destination directory based on file extension.")
    parser.add_argument("source_dir", 
                        type=Path, # Uses pathlib.Path to convert the argument
                        help="The source directory containing files to organize.")
    parser.add_argument("dest_dir", 
                        type=Path, 
                        help="The base destination where organized sub-folders will be created.")
    parser.add_argument("--dry-run", 
                        action="store_true", 
                        help="Simulate the organization process without actually moving files.")
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

    # Adjusts the logger level based on the -v/--verbose argument
    logger.setLevel(args.loglevel)

    try:
        # Creates the organizer instance with the parsed arguments
        organizer = FileOrganizer(args.source_dir, args.dest_dir, args.dry_run)
        # Start the organization process
        organizer.organize()
        logger.info("Organization process completed successfully.")
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
            
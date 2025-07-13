import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class FileOrganizer:
    """ 
    Contains the core logic for organizing files, moving them from 
    the source directory to the destination based on an extension map."
    """
    def __init__(self, source_dir: Path, dest_dir: Path):
        """
        Initializes the organizer.

        Args:
            source_dir: Source directory containing the files.
            dest_dir: Destination directory where the files will be moved.
        
        Raises:
            ValueError: If the source or destination directories are invalid..
        """
        if not source_dir.is_dir():
            raise ValueError(f"Source directory does not exist or is not a directory: {source_dir}")
        if dest_dir.exists() and not dest_dir.is_dir():
            raise ValueError(f"Destination path exists but is not a directory: {dest_dir}")

        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.files_moved = 0
        self.files_skipped = 0

        logger.info(f"Core organizer initialized. Source: '{self.source_dir}', Destination: '{self.dest_dir}'")
    
    def organize(self, extension_map: Dict[str, str], dry_run: bool = False):
        """
        Executes the file organization process.
        
        Args:
            extension_map: Dictionary mapping extensions to folder names.
            dry_run: If True, simulates the actions without moving files.
        """
        logger.info("Starting file organization process...")
        self.files_moved = 0
        self.files_skipped = 0
        
        total_scanned = 0
        for item_path in self.source_dir.rglob('*'):
            if item_path.is_file():
                total_scanned += 1
                self._process_file(item_path, extension_map, dry_run)
        
        log_prefix = "Dry run finished." if dry_run else "Organization finished."
        logger.info(f"--- {log_prefix} ---")
        logger.info(f"Total files scanned: {total_scanned}")
        if dry_run:
            logger.info(f"Files that would be moved or renamed: {self.files_moved}")
            logger.info(f"Files that would be skipped (duplicates): {self.files_skipped}")
        else:
            logger.info(f"Files successfully moved or renamed: {self.files_moved}")
            logger.info(f"Identical duplicate files skipped: {self.files_skipped}")
    
    def _process_file(self, file_path: Path, extension_map: Dict[str, str], dry_run: bool):
        """Processes a single file, deciding whether to move it or ignore it."""
        extension = file_path.suffix.lower()
        if not extension or extension not in extension_map:
            logger.debug(f"Ignoring file '{file_path.name}' (unmapped or no extension).")
            return

        dest_folder_name = extension_map[extension]
        destination_category_folder = self.dest_dir / dest_folder_name

        self._move_file_with_deduplication(file_path, destination_category_folder, dry_run)
    
    def _move_file_with_deduplication(self, source_path: Path, dest_folder: Path, dry_run: bool):
        """Moves a file, handling duplicates."""
        prospective_dest_path = dest_folder / source_path.name
        
        if prospective_dest_path.exists():
            source_hash = self._calculate_file_hash(source_path)
            dest_hash = self._calculate_file_hash(prospective_dest_path)
            
            if source_hash and source_hash == dest_hash:
                logger.info(f"Skipping identical file: {source_path.name}")
                self.files_skipped += 1
                return
            else:
                # Renames if the name exists but the content is different
                final_dest_path = self._get_unique_destination_path(dest_folder, source_path.name)
        else:
            final_dest_path = prospective_dest_path

        if dry_run:
            if final_dest_path.name != source_path.name:
                logger.info(f"[DRY RUN] Would move '{source_path.name}' to '{final_dest_path}' (renamed).")
            else:
                logger.info(f"[DRY RUN] Would move '{source_path.name}' to '{final_dest_path}'.")
            self.files_moved += 1 # CCounted as "processed" in dry-run.
            return

        logger.info(f"Moving '{source_path.name}' to '{final_dest_path}'")
        try:
            dest_folder.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_path), str(final_dest_path))
            self.files_moved += 1
        except (shutil.Error, OSError) as e:
            logger.error(f"Error moving file {source_path.name}: {e}")
            self.files_skipped += 1
    
    def _calculate_file_hash(self, file_path: Path) -> Optional[str]:
        """Calculates the SHA256 hash of a file."""
        hasher = hashlib.new("sha256")
        try:
            with file_path.open('rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except OSError as e:
            logger.error(f"Could not calculate hash for {file_path}: {e}")
            return None
    
    def _get_unique_destination_path(self, destination_folder: Path, original_file_name: str) -> Path:
        """Generates a unique filename if the original already exists."""
        base_name = Path(original_file_name).stem
        extension = Path(original_file_name).suffix
        counter = 1
        potential_dest_path = destination_folder / original_file_name
        while potential_dest_path.exists():
            new_name = f"{base_name}({counter}){extension}"
            potential_dest_path = destination_folder / new_name
            counter += 1
        return potential_dest_path
    
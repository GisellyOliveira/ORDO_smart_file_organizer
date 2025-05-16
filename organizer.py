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
            raise ValueError(f"Source directory does not exist or is not a directory: {source_dir}")
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
        Determines the top-level category folder within the destination directory
        for a given file, based on its extension.
        """
        extension = file_path.suffix.lower()

        if not extension:
            logger.debug(f"Ignoring file '{file_path.name}' (reason: no extension).")
            return None

        target_subfolder_name = EXTENSION_MAP.get(extension)

        if not target_subfolder_name:
            logger.debug(f"Ignoring file '{file_path.name}' (reason: extension '{extension}' not in EXTENSION_MAP).")
            return None

        return self.dest_dir / target_subfolder_name


    def _get_unique_destination_path(self, destination_folder: Path, original_file_name: str) -> Path:
        """
        Generates a unique file path in the destination folder if a file with the
        original_file_name already exists. Appends (1), (2), etc.
        """
        base_name = Path(original_file_name).stem
        extension = Path(original_file_name).suffix

        potential_dest_path = destination_folder / original_file_name
        counter = 1
        while potential_dest_path.exists():
            if counter > 1000: # Safety break
                logger.error(f"Could not find a unique name for {original_file_name} in {destination_folder} after 1000 attempts. Using original name, which may overwrite or fail.")
                return destination_folder / original_file_name # Fallback

            new_name = f"{base_name}({counter}){extension}"
            potential_dest_path = destination_folder / new_name
            counter += 1
        return potential_dest_path


    def _move_file_with_deduplication(self, source_file_path: Path, destination_folder: Path) -> bool:
        """
        Moves a single file to the designated destination folder,
        creating the folder if necessary. Handles duplicates.
        """
        target_file_name = source_file_path.name
        prospective_dest_path = destination_folder / target_file_name

        if self.dry_run:
            # --- PRINT DE DEBUG ADICIONADO ---
            print(f"ORGANIZER_DEBUG DRY_RUN: File='{target_file_name}', prospective_dest_path='{str(prospective_dest_path)}', prospective_dest_path.exists()='{prospective_dest_path.exists()}'")
            if prospective_dest_path.exists():
                logger.info(f"[DRY RUN] File '{target_file_name}' already exists at '{destination_folder}'. "
                            f"Would compare hashes: if different, it would be renamed and moved; "
                            f"if same, it would be skipped.")
            else:
                logger.info(f"[DRY RUN] Would move '{source_file_path.name}' to '{prospective_dest_path}'")
            return True

        final_dest_path_for_move = prospective_dest_path
        log_action_prefix = "Moving"

        if prospective_dest_path.exists():
            logger.debug(f"File '{target_file_name}' already exists at '{destination_folder}'. Comparing hashes...")
            source_hash = self._calculate_file_hash(source_file_path)
            dest_hash = self._calculate_file_hash(prospective_dest_path)

            # --- PRINT DE DEBUG ADICIONADO ---
            print(f"ORGANIZER_DEBUG _move: File='{target_file_name}', Source Hash='{source_hash}', Dest Hash='{dest_hash}', Hashes Equal?={source_hash == dest_hash}")

            if source_hash is None:
                logger.error(f"Skipping '{source_file_path.name}' due to error calculating its hash.")
                return False
            if dest_hash is None:
                logger.error(f"Skipping '{source_file_path.name}'. Could not calculate hash for existing destination file '{prospective_dest_path.name}'.")
                return False

            if source_hash == dest_hash:
                # --- PRINT DE DEBUG ADICIONADO ---
                print(f"ORGANIZER_DEBUG _move: Hashes são IGUAIS para {target_file_name}, pulando.")
                logger.info(f"Skipping identical file (same name '{target_file_name}', same hash) "
                            f"Source: '{source_file_path}'. Destination: '{prospective_dest_path}'.")
                self.skipped_identical_duplicates += 1
                return False
            else: # Hashes diferentes
                # --- PRINT DE DEBUG ADICIONADO ---
                print(f"ORGANIZER_DEBUG _move: Hashes são DIFERENTES para {target_file_name}, tentando renomear.")
                logger.info(f"File '{target_file_name}' exists at '{destination_folder}' but with different content (hashes differ). Renaming source before move.")

                path_antes_unique = final_dest_path_for_move # Guardar para debug
                final_dest_path_for_move = self._get_unique_destination_path(destination_folder, target_file_name)
                # --- PRINT DE DEBUG ADICIONADO ---
                print(f"ORGANIZER_DEBUG _move: path_antes_unique='{str(path_antes_unique)}', final_dest_path_for_move_APOS_UNIQUE='{str(final_dest_path_for_move)}'")

                if final_dest_path_for_move.name != target_file_name:
                    log_action_prefix = "Moving (renamed)"
                    # --- PRINT DE DEBUG ADICIONADO ---
                    print(f"ORGANIZER_DEBUG _move: log_action_prefix atualizado para '{log_action_prefix}' porque '{final_dest_path_for_move.name}' != '{target_file_name}'")
                else:
                    # --- PRINT DE DEBUG ADICIONADO ---
                    print(f"ORGANIZER_DEBUG _move: log_action_prefix NÃO atualizado. final_dest_path_for_move.name='{final_dest_path_for_move.name}', target_file_name='{target_file_name}'")

        logger.info(f"{log_action_prefix} '{source_file_path.name}' to '{final_dest_path_for_move}'")

        try:
            destination_folder.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_file_path), str(final_dest_path_for_move))
            logger.info(f"Successfully moved '{source_file_path.name}' to '{final_dest_path_for_move}'")
            self.files_successfully_moved_or_renamed += 1
            return True
        except shutil.Error as e:
            logger.error(f"Shutil Error moving file '{source_file_path.name}' to '{final_dest_path_for_move}': {e}")
        except OSError as e:
            logger.error(f"OS Error moving files '{source_file_path.name}' to '{final_dest_path_for_move}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error moving file '{source_file_path.name}' to '{final_dest_path_for_move}': {e}",
                         exc_info=True)
            return False
        return False # Adicionado para garantir que todos os caminhos retornem um bool


    def organize(self) -> None:
        """
        Scans the source directory and its subdirectories recursively.
        """
        logger.info(f"Starting recursive organization process for '{self.source_dir}'...")

        total_files_scanned = 0
        files_considered_for_processing = 0
        files_ignored_by_rule = 0

        self.files_successfully_moved_or_renamed = 0
        self.skipped_identical_duplicates = 0

        for item_path in self.source_dir.rglob('*'):
            if item_path.is_file():
                total_files_scanned += 1
                logger.debug(f"Scanning file: '{item_path}'")

                destination_folder = self._get_destination_folder_or_ignore(item_path)

                # --- PRINT DE DEBUG ADICIONADO ---
                # print(f"ORGANIZER_DEBUG organize - File: {item_path.name}, Determined Dest folder: {destination_folder}")

                if destination_folder is None:
                    files_ignored_by_rule += 1
                    continue

                files_considered_for_processing += 1
                self._move_file_with_deduplication(item_path, destination_folder)

            elif item_path.is_dir():
                logger.debug(f"Scanning within directory: '{item_path}'.")
            else:
                logger.warning(f"Skipping item that is not a file or directory: '{item_path}'")

        log_summary_prefix = "Dry run finished." if self.dry_run else "Organization finished."
        logger.info(f"--- {log_summary_prefix} ---")
        logger.info(f"Total files scanned: {total_files_scanned}")
        logger.info(f"Files ignored by extension rules: {files_ignored_by_rule}")

        if self.dry_run:
            logger.info(f"Files that would be considered for moving/renaming (passed extension filter): {files_considered_for_processing}")
            logger.info(f"   (In dry run, detailed duplicate checks and renaming are simulated and logged per file.)")
        else:
            logger.info(f"Files successfully moved or renamed: {self.files_successfully_moved_or_renamed}")
            logger.info(f"Identical duplicate files skipped: {self.skipped_identical_duplicates}")

        unaccounted_for = files_considered_for_processing - (self.files_successfully_moved_or_renamed + self.skipped_identical_duplicates)
        if not self.dry_run and unaccounted_for > 0:
            # Este log pode ser útil para identificar arquivos que foram considerados mas não se encaixaram
            # nas categorias de movido/renomeado ou pulado por duplicata idêntica (ex: erro de hash)
            logger.info(f"Files considered but not moved/skipped (e.g., due to errors): {unaccounted_for}")


def main() -> None:
    """
    Sets arguments, creates the organizer and starts the process.
    """
    parser = argparse.ArgumentParser(
        description="Organizes files from a source directory (recursively) into subdirectories "
                    "within a destination directory based on file extension, handling duplicates.")
    parser.add_argument("source_dir",
                        type=Path,
                        help="The source directory containing files to organize.")
    parser.add_argument("dest_dir",
                        type=Path,
                        help="The base destination where organized sub-folders will be created.")
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Simulates the organization process without actually copying files.")
    parser.add_argument(
        "-v", "--verbose",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
        help="Increase output verbosity to DEBUG level."
        )

    args = parser.parse_args()

    # Configura o nível de log do logger principal do módulo
    # Se você tiver outros loggers, eles podem precisar ser configurados separadamente
    # ou herdarão do root logger se a propagação estiver habilitada.
    logging.getLogger().setLevel(args.loglevel) # Configura o root logger
    logger.setLevel(args.loglevel) # Configura o logger específico do módulo

    # Se você quiser que os logs de DEBUG de outras bibliotecas (como 'shutil' se ele logasse)
    # também apareçam, configurar o root logger é uma boa ideia.
    # Se quiser apenas os logs do seu módulo em DEBUG, configurar apenas `logger.setLevel(args.loglevel)` é suficiente.

    try:
        organizer = FileOrganizer(args.source_dir, args.dest_dir, args.dry_run)
        organizer.organize()
        logger.info("Organization process completed.")
    except ValueError as e:
        logger.critical(f"Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An unexpected critical error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
    
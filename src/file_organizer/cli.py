import argparse
import logging
import sys
from pathlib import Path
#from typing import Dict

from . import config
from .core import FileOrganizer

logger = logging.getLogger(__name__)

def setup_logging(level: int):
    """Sets up basic logging for the application."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def handle_interactive_edit(current_map: Dict[str, str]) -> bool:
    """
    Handles the interactive editing flow of existing mappings.
    Modifies the `current_map` dictionary directly.
    Returns True if any changes were made.
    """
    try:
        review_choice = input("Review or modify current extension mappings? (yes/No, default: No): ").strip().lower()
        first_char = review_choice[0] if review_choice else 'n'
    except EOFError:
        logger.warning("\nInput stream closed (EOF). Skipping review.")
        return False
        
    if first_char != 'y':
        logger.info("Skipping review of existing mappings.")
        return False
    
    map_changed = False
    logger.info("--- Review/Modify Existing Mappings ---")
    if not current_map:
        logger.info("No mappings currently defined.")
    else:
        for ext, folder in sorted(current_map.items()):
            logger.info(f"  '{ext}' -> '{folder}'")
    
    while True:
        try:
            ext_to_modify = input("Enter extension to modify (e.g., .pdf), or type 'done' to finish: ").strip().lower()
        except EOFError:
            logger.warning("\nInput stream closed (EOF). Exiting modification mode.")
            break

        if ext_to_modify == 'done':
            break

        if not ext_to_modify.startswith('.') or len(ext_to_modify) < 2:
            if ext_to_modify:
                logger.warning(f"Invalid extension format: '{ext_to_modify}'.")
            continue

        if ext_to_modify in current_map:
            current_folder = current_map[ext_to_modify]
            prompt = (
                f"  Extension '{ext_to_modify}' maps to '{current_folder}'.\n"
                f"  New folder (Enter to keep, 'ignore' to remove): "
            )
            try:
                new_folder = input(prompt).strip()
            except EOFError:
                logger.warning("\nInput stream closed (EOF).")
                continue

            if not new_folder:
                logger.info(f"Mapping for '{ext_to_modify}' remains '{current_folder}'.")
            elif new_folder.lower() == 'ignore':
                del current_map[ext_to_modify]
                map_changed = True
                logger.info(f"Mapping for '{ext_to_modify}' removed for this session.")
            else:
                if current_folder != new_folder:
                    current_map[ext_to_modify] = new_folder
                    map_changed = True
                    logger.info(f"Mapping for '{ext_to_modify}' changed to '{new_folder}'.")
        else:
            logger.info(f"Extension '{ext_to_modify}' not currently mapped.")
            
    logger.info("Finished reviewing/modifying mappings.")
    return map_changed

def handle_unmapped_extensions(source_dir: Path, current_map: Dict[str, str]) -> bool:
    """
    Discovers unmapped extensions and asks the user how to handle them.
    Modifies the `current_map` dictionary directly.
    Returns True if any changes were made.
    """
    logger.info("Scanning for unmapped extensions...")
    found_extensions = {p.suffix.lower() for p in source_dir.rglob('*') if p.is_file() and p.suffix}
    unmapped = sorted(list(found_extensions - set(current_map.keys())))
    
    if not unmapped:
        logger.info("No unmapped extensions found.")
        return False

    map_changed = False
    logger.info("--- New/Unmapped Extensions Found ---")
    logger.info("The following unmapped extensions were discovered: " + ", ".join(unmapped))
    
    for ext in unmapped:
        try:
            prompt = f"Enter target folder for '{ext}' (or leave blank to ignore): "
            folder_name = input(prompt).strip()
            
            if not folder_name:
                logger.info(f"Extension '{ext}' will be ignored for this session.")
                continue

            invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
            if any(char in folder_name for char in invalid_chars) or folder_name.startswith('.') or folder_name.endswith('.'):
                logger.warning(f"Invalid folder name: '{folder_name}'. Skipping this extension.")
                continue
            
            current_map[ext] = folder_name
            map_changed = True
            logger.info(f"Extension '{ext}' will be organized into '{folder_name}'.")
        except EOFError:
            logger.warning("\nInput stream closed (EOF). Stopping interactive mapping.")
            break
            
    return map_changed

    def main():
        """Main entry point of the CLI application."""
        parser = argparse.ArgumentParser(
            description="Organizes files from a source directory into categorized subdirectories."
        )
        parser.add_argument("source_dir", type=Path, help="The source directory containing files to organize.")
        parser.add_argument("dest_dir", type=Path, help="The base destination directory for organized sub-folders.")
        parser.add_argument("--dry-run", action="store_true", help="Simulates the organization process without moving files.")
        parser.add_argument("-v", "--verbose", action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.INFO, help="Increase output verbosity to DEBUG level.")
    
        args = parser.parse_args()
    
        setup_logging(args.loglevel)
    
        try:
            # 1. Loads the initial configuration
            extension_map = config.load_extension_map()
        
            # 2. Runs the interactive flows to refine the map
            #map_changed_by_edit = handle_interactive_edit(extension_map)
            #map_changed_by_new = handle_unmapped_extensions(args.source_dir, extension_map)
            #map_was_changed = map_changed_by_edit or map_changed_by_new

            # 3. Initializes the 'worker' and runs the main logic
            organizer = FileOrganizer(args.source_dir, args.dest_dir)
            organizer.organize(extension_map, args.dry_run)

            # 4. Saves the configuration if it changed and if the user confirms
            #if map_was_changed and not args.dry_run:
                #try:
                    #save_choice = input("Save these new/updated mappings for future use? (y/N): ").strip().lower()
                    #if save_choice.startswith('y'):
                        #config.save_extension_map(extension_map)
                #except EOFError:
                    #logger.warning("Input stream closed (EOF). Configuration not saved.")

        except (ValueError, FileNotFoundError) as e:
            logger.critical(f"Configuration Error: {e}")
            sys.exit(1)
        except Exception as e:
            logger.critical(f"An unexpected critical error occurred: {e}", exc_info=True)
            sys.exit(1)

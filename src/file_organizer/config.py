import json
import logging
from pathlib import Path
from typing import Dict

from platformdirs import user_config_dir

# --- Logging Configuration ---
logger = logging.getLogger(__name__)

# --- Constants ---
APP_NAME = "File Organizer - CLI Version"
APP_AUTHOR = "Giselly Oliveira"
CONFIG_FILE_NAME = "extension_map_config.json"

# --- Extension to Folder Mapping ---
# This dictionary defines how files are categorized based on their extensions.
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
    '.json': "Data",
    '.xml': "Data",
    # Images
    '.jpg': "Images",
    '.jpeg': "Images",
    '.png': "Images",
    '.gif': "Images",
    '.bmp': "Images",
    '.tiff': "Images",
    '.webp': "Images",
    '.heic': "Images",
    # Vector Graphics & Design
    '.svg': "VectorGraphics",
    '.psd': "Design_Files",
    '.ai': "Design_Files",
    # Archives
    '.zip': "Archives",
    '.rar': "Archives",
    '.tar': "Archives",
    '.gz': "Archives",
    '.7z': "Archives",
    # Executables & Installers
    '.exe': "Executables_Installers",
    '.msi': "Executables_Installers",
    '.dmg': "Executables_Installers",
    '.pkg': "Executables_Installers",
    '.deb': "Executables_Installers",
    '.rpm': "Executables_Installers",
    '.jar': "Executables_Installers",
    # Audio
    '.mp3': "Music",
    '.wav': "Audio",
    '.aac': "Audio",
    '.flac': "Audio",
    '.ogg': "Audio",
    '.m4a': "Audio",
    # Videos
    '.mp4': "Videos",
    '.avi': "Videos",
    '.mkv': "Videos",
    '.mov': "Videos",
    '.wmv': "Videos",
    '.flv': "Videos",
    # Logs & Configs
    '.log': "LogFiles",
    '.yaml': "Configs",
    '.yml': "Configs",
    # Fonts
    '.ttf': "Fonts",
    '.otf': "Fonts",
}

def get_config_file_path() -> Path:
    """Determines the standardized path for the configuration file, 
    ensuring that the directory exists.""" 
    # uses platformdirs to find an appropriate user-specific config directory
    config_dir = Path(user_config_dir(APP_NAME, APP_AUTHOR, roaming=True))
    # Ensures the configuration directory is created if it does not exist
    config_dir.mkdir(parents=True, exist_ok=True) 
    return config_dir / CONFIG_FILE_NAME

def load_extension_map() -> Dict[str, str]:
    """
    Loads the extension map from the user's configuration file.


    If the configuration file exists and is valid, its contents are merged
    with the default map (user settings take precedence). 
    Otherwise, a copy of the default map is returned.
    """
    config_path = get_config_file_path()
    if config_path.exists() and config_path.is_file():
        try:
            with config_path.open('r', encoding='utf-8') as f:
                user_map = json.load(f)
            
            if isinstance(user_map, dict):
                logger.info(f"Loaded custom extension map from {config_path}")
                # Starts with a copy of the default and updates it with the user's preferences.
                combined_map = DEFAULT_EXTENSION_MAP.copy()
                combined_map.update(user_map)
                return combined_map
            else:
                logger.warning(
                    f"Configuration file {config_path} is not a valid JSON dictionary. "
                    f"Using default extension map."
                )
        except (json.JSONDecodeError, OSError) as e:
            logger.error(
                f"Error reading or decoding config from {config_path}: {e}. "
                f"Using default extension map."
            )
    else:
        logger.info("No custom configuration file found. Using default extension map.")
    
    return DEFAULT_EXTENSION_MAP.copy()

def save_extension_map(extension_map: Dict[str, str]) -> None:
    """
    Saves the provided extension map to the user's configuration file.

    Args:
        extension_map: The mapping dictionary to be saved.
    """
    config_path = get_config_file_path()
    try:
        with config_path.open('w', encoding='utf-8') as f:
            # Salva o JSON com indentação para ser legível por humanos
            json.dump(extension_map, f, indent=4, sort_keys=True)
        logger.info(f"Extension mappings saved to {config_path}")
    except OSError as e:
        logger.error(f"Error saving configuration to {config_path}: {e}", exc_info=True)

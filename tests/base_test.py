import unittest
from unittest.mock import MagicMock # It might be used in child tests
from pathlib import Path
from typing import Optional, Dict, Set # Dict might be helpful
import logging # Added to configure self.logger

from organizer import DEFAULT_EXTENSION_MAP

class BaseOrganizerTest(unittest.TestCase):
    """
    Base class for FileOrganizer tests, providing common setup, teardown,
    and helper methods for creating and managing mock objects.
    """

    def setUp(self) -> None:
        """
        Set up method executed before each individual test in subclasses.

        Initializes mock objects for source and destination directories,
        a variety of mock files with different extensions and properties,
        and a dictionary to manage pre-configured destination file path mocks.
        This ensures a clean and consistent environment for every test.
        """
        self.logger = logging.getLogger('organizer') # To be used with self.assertLogs in subclasses

        # Mock for the source directory Path object
        self.mock_source_dir = MagicMock(spec=Path, name="SourceDirMock")
        self.mock_source_dir.is_dir.return_value = True
        self.mock_source_dir.__str__.return_value = "/fake/source" # String representation for logs/paths

        # Mock for the base destination directory Path object
        self.mock_dest_dir = MagicMock(spec=Path, name="DestDirMock")
        self.mock_dest_dir.exists.return_value = False # Assumes base destination dir doesn't exist initially
        self.mock_dest_dir.is_dir.return_value = True # But if, by chance, it exists, then, it's a directory
        self.mock_dest_dir.__str__.return_value = "/fake/destination"

        # Dictionary to store pre-configured mock Path objects for specific destination *files*
        # This allows tests to define specific states (e.g., exists=True, specific hash)
        # for files that the organizer might encounter in the destination.
        self.configured_dest_file_paths: Dict[str, MagicMock] = {} 

        # --- Mocks for destination CATEGORY FOLDERS based on DEFAULT_EXTENSION_MAP ---
        # Dynamically create mocks for each unique category folder name in DEFAULT_EXTENSION_MAP
        self.category_folder_mocks: Dict[str, MagicMock] = {}
        unique_category_names: Set[str] = set(DEFAULT_EXTENSION_MAP.values())
        for category_name in unique_category_names:
            # Store the mock on self with a predictable attribute name, e.g., self.mock_dest_Documents
            attr_name = f"mock_dest_{category_name.replace(' ', '_').replace('-', '_')}" # Sanitize name for attribute
            folder_mock = self._create_mock_dest_category_folder(category_name)
            setattr(self, attr_name, folder_mock)
            self.category_folder_mocks[category_name] = folder_mock

        # --- Mock source files for various scenarios ---
        # Each mock file is created with a name, extension, a simulated path prefix,
        # and an optional (mocked) content hash.
        self.file_pdf1 = self._create_mock_file("report.pdf", ".pdf", path_prefix="source")
        self.file_docx1 = self._create_mock_file("letter.docx", ".docx", path_prefix="source")
        self.file_epub1 = self._create_mock_file("book.epub", ".epub", path_prefix="source/ebooks_folder")
        self.file_xlsx1 = self._create_mock_file("data.xlsx", ".xlsx", path_prefix="source")
        self.file_csv1 = self._create_mock_file("table.csv", ".csv", path_prefix="source/data_files")
        self.file_jpg1 = self._create_mock_file("image.jpg", ".jpeg", path_prefix="source") # Test case-insensitivity of ext
        self.file_png1 = self._create_mock_file("logo.png", ".png", path_prefix="source/assets")
        self.file_svg1 = self._create_mock_file("icon.svg", ".svg", path_prefix="source/vector")
        self.file_psd1 = self._create_mock_file("design.psd", ".psd", path_prefix="source/designs")
        self.file_zip1 = self._create_mock_file("files.zip", ".zip", path_prefix="source")
        self.file_exe1 = self._create_mock_file("installer.exe", ".exe", path_prefix="source/installers")
        self.file_mp3_1 = self._create_mock_file("song.mp3", ".mp3", path_prefix="source/audio_files")
        self.file_wav1 = self._create_mock_file("sound.wav", ".wav", path_prefix="source/audio_files")
        self.file_mp4_1 = self._create_mock_file("movie.mp4", ".mp4", path_prefix="source/video_files")
        self.file_log1 = self._create_mock_file("server.log", ".log", path_prefix="source/logs")
        self.file_json1 = self._create_mock_file("settings.json", ".json", path_prefix="source/configs") # Note: DEFAULT_EXTENSION_MAP has .json -> Data
        self.file_yaml1 = self._create_mock_file("app.yaml", ".yaml", path_prefix="source/configs")
        self.file_ttf1 = self._create_mock_file("myfont.ttf", ".ttf", path_prefix="source/fonts_folder")
        
        # Files that should be ignored by the organizer
        self.file_no_ext = self._create_mock_file("no_extension_file", "", path_prefix="source")
        self.file_unmapped_ext = self._create_mock_file("backup.dat", ".dat", path_prefix="source")

        # Files specifically for testing deduplication logic
        self.file_dup_txt_src = self._create_mock_file("readme_dup.txt", ".txt", path_prefix="source", content_hash="same_hash_for_txt_dup")
        self.file_dup_img_src = self._create_mock_file("photo_dup.png", ".png", path_prefix="source", content_hash="image_hash_source_A")

        # Default list of files that `mock_source_dir.rglob('*')` will return
        self.all_source_files_for_setup = [
            self.file_pdf1, self.file_docx1, self.file_epub1, self.file_xlsx1, self.file_csv1,
            self.file_jpg1, self.file_png1, self.file_svg1, self.file_psd1, self.file_zip1,
            self.file_exe1, self.file_mp3_1, self.file_wav1, self.file_mp4_1, self.file_log1,
            self.file_json1, self.file_yaml1, self.file_ttf1,
            self.file_no_ext, self.file_unmapped_ext,
            self.file_dup_txt_src, self.file_dup_img_src,
        ]
        self.mock_source_dir.rglob.return_value = self.all_source_files_for_setup

        # Configure the division operator (/) for the main destination directory mock
        # to return the appropriate category folder mock.
        self.mock_dest_dir.__truediv__.side_effect = self._master_destination_category_folder_division

    def tearDown(self) -> None:
        """
        Clean up method executed after each individual test.
        Clears the dictionary of pre-configured destination file paths to ensure
        test isolation.
        """
        self.configured_dest_file_paths.clear()

    def _mock_calculate_hash_side_effect(self, file_path_obj: Path, hash_algo: str = "sha256", buffer_size: int = 65536) -> Optional[str]:
        """
        Side effect function for mocking `FileOrganizer._calculate_file_hash`.
        Returns the `mocked_content_hash` attribute of the `file_path_obj` if it exists.
        This allows tests to predefine hash values for mock files.
        If `mocked_content_hash` is not present, it returns a predictable,
        name-based fallback hash. If `mocked_content_hash` is explicitly `None`,
        this function returns `None`, simulating a hash calculation error.

        Args:
            file_path_obj: The mock Path object for which to "calculate" the hash.
            hash_algo: The hashing algorithm (ignored by this mock).
            buffer_size: The buffer size for reading (ignored by this mock).

        Returns:
            The predefined mocked hash string, a fallback hash string, or None.
        """
        if hasattr(file_path_obj, 'mocked_content_hash'):
            return file_path_obj.mocked_content_hash
        else:
            # Fallback for mocks that don't have 'mocked_content_hash' explicitly set
            # (e.g., some intermediate destination path mocks or generic file mocks).
            return f"hash_for_{Path(str(file_path_obj)).name}"

    def _create_mock_file(self, name: str, suffix: str, path_prefix: str = "source", content_hash: Optional[str] = "default_hash") -> MagicMock:
        """
        Helper function to create a mock `pathlib.Path` object simulating a source file.

        Args:
            name: The file name (e.g., "report.pdf").
            suffix: The file extension including the dot (e.g., ".pdf").
            path_prefix: A string to simulate the file's parent directory structure
                         relative to a base "/fake/" path (e.g., "source", "source/subfolder").
            content_hash: The mock hash value for this file. If "default_hash" (the default),
                          a name-based hash is generated. Can be a specific string or `None`
                          to simulate hash calculation failure for this file.

        Returns:
            A `MagicMock` configured to behave like a file `Path` object.
        """
        base_path = "/fake" 
        full_path_str: str
        if path_prefix and path_prefix != ".": # Handle cases with and without path_prefix
            processed_path_prefix = path_prefix.strip('/')
            full_path_str = f"{base_path}/{processed_path_prefix}/{name}"
        else:
            full_path_str = f"{base_path}/{name}"

        mock_file = MagicMock(spec=Path, name=f"FileMock_{name.replace('.', '_')}")
        mock_file.name = name
        mock_file.suffix = suffix.lower() # Extensions are typically case-insensitive in practice
        mock_file.is_file.return_value = True
        mock_file.is_dir.return_value = False
        mock_file.__str__.return_value = full_path_str # Crucial for string-based path operations
        mock_file.exists.return_value = True # Source files are assumed to always exist

        if content_hash == "default_hash":
            mock_file.mocked_content_hash = f"hash_for_{name.replace('.', '_')}"
        else:
            mock_file.mocked_content_hash = content_hash # Allows setting a specific hash or None
        return mock_file

    def _create_mock_dest_category_folder(self, subfolder_name: str) -> MagicMock:
        """
        Creates a mock `Path` object representing a destination category FOLDER
        (e.g., "/fake/destination/Images").

        Args:
            subfolder_name: The name of the category subfolder (e.g., "Images").

        Returns:
            A `MagicMock` configured as a destination category folder.
        """
        mock_folder_path = MagicMock(spec=Path, name=f"DestFolderMock_{subfolder_name.replace(' ', '_').replace('-', '_')}")
        mock_folder_path.__str__.return_value = f"{self.mock_dest_dir}/{subfolder_name}"
        mock_folder_path.name = subfolder_name
        mock_folder_path.exists.return_value = False # Category folders don't exist by default
        mock_folder_path.is_dir.return_value = True # But in case they exist, they are directories

        # This handler is called when `mock_folder_path / "filename.ext"` is executed.
        # It captures `mock_folder_path` (the left operand) from its closure.
        # The `right_operand` is what's on the right side of the '/'.
        def truediv_handler_for_this_folder(right_operand):
            return self._specific_destination_file_division(mock_folder_path, right_operand)

        mock_folder_path.__truediv__.side_effect = truediv_handler_for_this_folder
        return mock_folder_path

    def _master_destination_category_folder_division(self, subfolder_name_str: str) -> MagicMock:
        """
        Side effect for `self.mock_dest_dir.__truediv__`.
        Called when `self.mock_dest_dir / "CategoryFolderName"` is executed.
        Returns the appropriate pre-defined mock for the category folder.

        Args:
            subfolder_name_str: The name of the category subfolder.

        Returns:
            The `MagicMock` representing that category folder.
        """
        if subfolder_name_str in self.category_folder_mocks:
            return self.category_folder_mocks[subfolder_name_str]
        else:
            # This case IS expected to be hit when testing interactive mapping
            # of new extensions. The log is still useful for debugging.
            self.logger.info(
                f"Dynamically creating and registering mock for new category folder: '{subfolder_name_str}'."
            )
            # Create a new mock for the folder...
            new_folder_mock = self._create_mock_dest_category_folder(subfolder_name_str)
            # ...and REGISTER it so it becomes a "known" folder for this test run.
            self.category_folder_mocks[subfolder_name_str] = new_folder_mock
            return new_folder_mock

    def _specific_destination_file_division(self, current_dest_category_folder_mock: MagicMock, file_name_or_path_obj: any) -> MagicMock:
        """
        Side effect for `destination_category_folder_mock.__truediv__`.
        Called when `category_folder_mock / "filename.ext"` is executed.
        
        Checks `self.configured_dest_file_paths` for a pre-configured mock for the
        resulting file path. If found, returns it. Otherwise, creates and returns
        a generic mock for the file (defaulting to `exists=False`).

        Args:
            current_dest_category_folder_mock: The mock of the destination category folder
                                               (the left operand of /).
            file_name_or_path_obj: The file name or Path object being appended
                                   (the right operand of /).

        Returns:
            A `MagicMock` representing the file within the destination category folder.
        """
        file_name_str = str(file_name_or_path_obj)
        # If file_name_or_path_obj is a mock Path itself, use its .name attribute
        if isinstance(file_name_or_path_obj, MagicMock) and hasattr(file_name_or_path_obj, 'name'):
            file_name_str = file_name_or_path_obj.name # Extract name if it's a mock Path

        # Use the string representation of the full path as a unique key
        full_file_path_key = f"{str(current_dest_category_folder_mock)}/{file_name_str}"

        if full_file_path_key in self.configured_dest_file_paths:
            return self.configured_dest_file_paths[full_file_path_key]

        # If not pre-configured, create a generic mock for this destination file path
        generic_file_mock = MagicMock(spec=Path, name=f"DestFileMock_Generic_{file_name_str.replace('.', '_')}")
        generic_file_mock.__str__.return_value = full_file_path_key
        generic_file_mock.name = file_name_str
        generic_file_mock.stem = Path(file_name_str).stem
        generic_file_mock.suffix = Path(file_name_str).suffix
        generic_file_mock.exists.return_value = False # Default: file does not exist in destination
        # No `mocked_content_hash` by default; `_mock_calculate_hash_side_effect` will use its fallback.
        return generic_file_mock

    def _configure_destination_file_mock(self, dest_category_folder_mock: MagicMock, file_name: str, exists: bool, content_hash: Optional[str] = "default_hash_for_dest_file") -> MagicMock:
        """
        Helper to create, configure, and register a mock for a specific
        destination file path in `self.configured_dest_file_paths`.

        This allows tests to define the state (existence, hash) of files
        that `FileOrganizer` might encounter or try to create in the destination.

        Args:
            dest_category_folder_mock: The mock of the category folder where the file resides.
            file_name: The name of the file.
            exists: Boolean indicating if this mock file should "exist".
            content_hash: The mock hash for this file. If "default_hash_for_dest_file",
                          no `mocked_content_hash` attribute is set, letting
                          `_mock_calculate_hash_side_effect` use its name-based fallback.
                          Can be a specific string or `None`.

        Returns:
            The configured `MagicMock` for the destination file.
        """
        full_path_str = f"{str(dest_category_folder_mock)}/{file_name}"
        
        file_mock = MagicMock(spec=Path, name=f"ConfiguredDestFile_{file_name.replace('.', '_')}")
        file_mock.__str__.return_value = full_path_str
        file_mock.name = file_name
        file_mock.stem = Path(file_name).stem
        file_mock.suffix = Path(file_name).suffix
        file_mock.exists.return_value = exists
        
        # Only set mocked_content_hash if a specific value (including None) is provided.
        # This allows the fallback hash in _mock_calculate_hash_side_effect to be used
        # if no specific hash behavior is needed for the destination file.
        if content_hash != "default_hash_for_dest_file": # Only set if not the placeholder default
            file_mock.mocked_content_hash = content_hash
        
        self.configured_dest_file_paths[full_path_str] = file_mock
        return file_mock

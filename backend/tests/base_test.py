import logging
import unittest
from unittest.mock import MagicMock 
from pathlib import Path
from typing import Optional, Dict, Set 

from src.file_organizer.config import DEFAULT_EXTENSION_MAP


class BaseOrganizerTest(unittest.TestCase):
    """
    Provides a common foundation for the application's test suites.

    This base class handles the setup of recurring mock objects, such as
    source/destination directories and a standard set of mock files.
    It also provides helper methods for creating and managing these mocks,
    ensuring a consistent and clean testing environment for each test case.
    """

    def setUp(self) -> None:
        """
        Set up method executed before each individual test in subclasses.

        Initializes mock objects for source and destination directories,
        a variety of mock files with different extensions and properties,
        and a dictionary to manage pre-configured destination file path mocks.
        This ensures a clean and consistent environment for every test.
        """
        self.logger = logging.getLogger('file_organizer') 

        # --- Core Directory Mocks ---
        self.mock_source_dir = MagicMock(spec=Path, name="SourceDirMock")
        self.mock_source_dir.is_dir.return_value = True
        self.mock_source_dir.__str__.return_value = "/fake/source"

        self.mock_dest_dir = MagicMock(spec=Path, name="DestDirMock")
        self.mock_dest_dir.exists.return_value = False 
        self.mock_dest_dir.is_dir.return_value = True
        self.mock_dest_dir.__str__.return_value = "/fake/destination"

        # --- Mock Management Dictionaries ---
        # Stores pre-configured mocks for destination files to simulate existing files.
        self.configured_dest_file_paths: Dict[str, MagicMock] = {} 
        # Stores mocks for destination category folders, created dynamically.
        self.category_folder_mocks: Dict[str, MagicMock] = {}
        
        self._setup_category_folder_mocks()
        self._setup_source_file_mocks()

        # Configure the path division operator (/) for the main destination mock.
        self.mock_dest_dir.__truediv__.side_effect = self._master_destination_category_folder_division

    def tearDown(self) -> None:
        """
        Cleans up configured destination file mocks after each test.
        
        This ensures that tests do not interfere with one another's
        pre-configured destination file states.
        """
        self.configured_dest_file_paths.clear()
    
    def _setup_category_folder_mocks(self) -> None:
        """Dynamically creates mocks for destination category folders."""
        unique_category_names: Set[str] = set(DEFAULT_EXTENSION_MAP.values())
        for category_name in unique_category_names:
            folder_mock = self._create_mock_dest_category_folder(category_name)
            self.category_folder_mocks[category_name] = folder_mock
    
    def _setup_source_file_mocks(self) -> None:
        """Creates a standard set of mock source files ofr various test scenarios."""
        self.file_pdf1 = self._create_mock_file("report.pdf", ".pdf")
        self.file_png1 = self._create_mock_file("logo.png", ".png", "source/assets")
        self.file_no_ext = self._create_mock_file("no_extension_file", "")
        self.file_unmapped_ext = self._create_mock_file("backup.dat", ".dat")
        self.file_dup_txt_src = self._create_mock_file("readme_dup.txt", ".txt", content_hash="same_hash_for_txt_dup")
        self.file_dup_img_src = self._create_mock_file("photo_dup.png", ".png", content_hash="image_hash_source_A")
        
        # This list can be used by tests that need to simulate a full directory scan.
        self.all_source_files_for_setup = [
            self.file_pdf1, self.file_png1, self.file_no_ext,
            self.file_unmapped_ext, self.file_dup_txt_src, self.file_dup_img_src,
        ]
        # By default, rglob returns the full list of mock files.
        self.mock_source_dir.rglob.return_value = self.all_source_files_for_setup

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
        return f"hash_for_{Path(str(file_path_obj)).name}"

    def _create_mock_file(self, name: str, suffix: str, path_prefix: str = "source", content_hash: Optional[str] = "default_hash") -> MagicMock:
        """
        Factory method to create a configured `MagicMock` simulating a `pathlib.Path` file object.

        Args:
            name: The file's name (e.g., "report.pdf").
            suffix: The file's extension (e.g., ".pdf").
            path_prefix: The simulated parent directory structure.
            content_hash: A specific hash value for the mock, or `None` to
                          simulate a hashing failure.

        Returns:
            A configured `MagicMock` instance.
        """
        full_path_str = f"/fake/{path_prefix.strip('/')}/{name}" if path_prefix else f"/fake/{name}"

        mock_file = MagicMock(spec=Path, name=f"FileMock_{name.replace('.', '_')}")
        mock_file.name = name
        mock_file.suffix = suffix.lower() 
        mock_file.is_file.return_value = True
        mock_file.is_dir.return_value = False
        mock_file.__str__.return_value = full_path_str 
        mock_file.exists.return_value = True 

        mock_file.mocked_content_hash = content_hash if content_hash != "default_hash" else f"hash_for_{name}"
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
        mock_folder = MagicMock(spec=Path, name=f"DestFolderMock_{subfolder_name}")
        mock_folder.__str__.return_value = f"{self.mock_dest_dir}/{subfolder_name}"
        mock_folder.is_dir.return_value = True

        # Configure the '/' operator to chain into the file resolution logic.
        mock_folder.__truediv__.side_effect = lambda file_name: self._specific_destination_file_division(mock_folder, file_name)
        return mock_folder

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
            self.logger.info(
                f"Dynamically creating and registering mock for new category folder: '{subfolder_name_str}'."
            )
            new_folder_mock = self._create_mock_dest_category_folder(subfolder_name_str)
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
        if isinstance(file_name_or_path_obj, MagicMock) and hasattr(file_name_or_path_obj, 'name'):
            file_name_str = file_name_or_path_obj.name 
        
        full_file_path_key = f"{str(current_dest_category_folder_mock)}/{file_name_str}"

        if full_file_path_key in self.configured_dest_file_paths:
            return self.configured_dest_file_paths[full_file_path_key]

        generic_file_mock = MagicMock(spec=Path, name=f"DestFileMock_Generic_{file_name_str.replace('.', '_')}")
        generic_file_mock.__str__.return_value = full_file_path_key
        generic_file_mock.name = file_name_str
        generic_file_mock.stem = Path(file_name_str).stem
        generic_file_mock.suffix = Path(file_name_str).suffix
        generic_file_mock.exists.return_value = False 
        
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
        
        if content_hash != "default_hash_for_dest_file": 
            file_mock.mocked_content_hash = content_hash
        
        self.configured_dest_file_paths[full_path_str] = file_mock
        return file_mock

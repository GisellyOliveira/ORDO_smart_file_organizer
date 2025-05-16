import unittest
from unittest.mock import patch, MagicMock, call
import logging
from pathlib import Path
from typing import Optional
from organizer import FileOrganizer

# Get the logger as defined in the organizer module
logger = logging.getLogger('organizer')

class TestFileOrganizer(unittest.TestCase):
    """
    Comprehensive test suite for the FileOrganizer class.

    This suite focuses on testing the core logic of FileOrganizer, including:
    - Initialization with valid and invalid parameters.
    - Basic file organization and movement.
    - Handling of ignored files (no extension, unmapped extension).
    - Recursive processing of source directories (simulated via rglob).
    - Dry-run mode functionality and logging.
    - Deduplication logic:
        - Skipping identical files (same name, same hash).
        - Renaming conflicting files (same name, different hash).
    - Error handling for:
        - Hash calculation failures (for both source and destination files).
        - File system operation errors during move (e.g., shutil.Error).
    
    Mocks are used extensively to isolate FileOrganizer from the actual
    file system and external dependencies like `hashlib`, ensuring tests are
    deterministic and fast.
    """

    def setUp(self) -> None:
        """
        Set up method executed before each individual test.

        Initializes mock objects for source and destination directories,
        a variety of mock files with different extensions and properties,
        and a dictionary to manage pre-configured destination file path mocks.
        This ensures a clean and consistent environment for every test.
        """
        # Mock for the source directory Path object
        self.mock_source_dir = MagicMock(spec=Path, name="SourceDirMock")
        self.mock_source_dir.is_dir.return_value = True
        self.mock_source_dir.__str__.return_value = "/fake/source" # String representation for logs/paths

        # Mock for the base destination directory Path object
        self.mock_dest_dir = MagicMock(spec=Path, name="DestDirMock")
        self.mock_dest_dir.exists.return_value = False # Assumes base destination dir doesn't exist initially
        self.mock_dest_dir.is_dir.return_value = True  # But if it were to exist, it's a directory
        self.mock_dest_dir.__str__.return_value = "/fake/destination"

        # Dictionary to store pre-configured mock Path objects for specific destination *files*
        # This allows tests to define specific states (e.g., exists=True, specific hash)
        # for files that the organizer might encounter in the destination.
        self.configured_dest_file_paths = {}

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
        self.file_json1 = self._create_mock_file("settings.json", ".json", path_prefix="source/configs")
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

        # --- Mocks for destination CATEGORY FOLDERS ---
        # These mocks represent the category folders (e.g., "Documents", "Images")
        # within the main destination directory.
        self.mock_dest_textfiles = self._create_mock_dest_category_folder("TextFiles")
        self.mock_dest_documents = self._create_mock_dest_category_folder("Documents")
        self.mock_dest_ebooks = self._create_mock_dest_category_folder("Ebooks")
        self.mock_dest_spreadsheets = self._create_mock_dest_category_folder("Spreadsheets")
        self.mock_dest_data = self._create_mock_dest_category_folder("Data")
        self.mock_dest_images = self._create_mock_dest_category_folder("Images")
        self.mock_dest_vectorgraphics = self._create_mock_dest_category_folder("VectorGraphics")
        self.mock_dest_design_files = self._create_mock_dest_category_folder("Design_Files")
        self.mock_dest_archives = self._create_mock_dest_category_folder("Archives")
        self.mock_dest_executables_installers = self._create_mock_dest_category_folder("Executables_Installers")
        self.mock_dest_music = self._create_mock_dest_category_folder("Music")
        self.mock_dest_audio = self._create_mock_dest_category_folder("Audio")
        self.mock_dest_videos = self._create_mock_dest_category_folder("Videos")
        self.mock_dest_logfiles = self._create_mock_dest_category_folder("LogFiles")
        self.mock_dest_configs = self._create_mock_dest_category_folder("Configs")
        self.mock_dest_fonts = self._create_mock_dest_category_folder("Fonts")

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
        mock_folder_path = MagicMock(spec=Path, name=f"DestFolderMock_{subfolder_name}")
        mock_folder_path.__str__.return_value = f"{self.mock_dest_dir}/{subfolder_name}"
        mock_folder_path.name = subfolder_name
        mock_folder_path.exists.return_value = False # Category folders don't exist by default
        mock_folder_path.is_dir.return_value = True  # But if they were to exist, they are directories

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
        mapping = {
            "TextFiles": self.mock_dest_textfiles, "Documents": self.mock_dest_documents,
            "Ebooks": self.mock_dest_ebooks, "Spreadsheets": self.mock_dest_spreadsheets,
            "Data": self.mock_dest_data, "Images": self.mock_dest_images,
            "VectorGraphics": self.mock_dest_vectorgraphics, "Design_Files": self.mock_dest_design_files,
            "Archives": self.mock_dest_archives, "Executables_Installers": self.mock_dest_executables_installers,
            "Music": self.mock_dest_music, "Audio": self.mock_dest_audio,
            "Videos": self.mock_dest_videos, "LogFiles": self.mock_dest_logfiles,
            "Configs": self.mock_dest_configs, "Fonts": self.mock_dest_fonts,
        }
        # Fallback to creating a new mock if not in mapping (shouldn't happen with EXTENSION_MAP)
        return mapping.get(subfolder_name_str, self._create_mock_dest_category_folder(subfolder_name_str))

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
        if content_hash != "default_hash_for_dest_file":
            file_mock.mocked_content_hash = content_hash
        
        self.configured_dest_file_paths[full_path_str] = file_mock
        return file_mock

    # --- Test Methods ---
    def test_init_success(self):
        """Tests successful initialization of FileOrganizer with valid parameters."""
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
        self.assertEqual(organizer.source_dir, self.mock_source_dir)
        self.assertEqual(organizer.dest_dir, self.mock_dest_dir)
        self.assertFalse(organizer.dry_run, "dry_run should be False by default.")
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)
    
    def test_init_invalid_source_dir(self):
        """Tests FileOrganizer initialization with a non-existent/invalid source directory."""
        self.mock_source_dir.is_dir.return_value = False # Simulate invalid source
        with self.assertRaisesRegex(ValueError, "Source directory does not exist or is not a directory"):
            FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
    
    def test_init_dest_is_file(self):
        """Tests FileOrganizer initialization when destination path exists but is a file, not a directory."""
        self.mock_dest_dir.exists.return_value = True
        self.mock_dest_dir.is_dir.return_value = False # Simulate destination is a file
        with self.assertRaisesRegex(ValueError, "Destination path exists but is not a directory"):
            FileOrganizer(self.mock_source_dir, self.mock_dest_dir)

    @patch('organizer.shutil.move')
    def test_organize_moves_and_ignores_files(self, mock_shutil_move: MagicMock):
        """
        Tests the core organization logic:
        - Files with mapped extensions are moved to their respective category folders.
        - Files in subdirectories of the source are processed.
        - Files without extensions or with unmapped extensions are ignored.
        - Destination category folders are created if they don't exist.
        Assumes no pre-existing files in the destination for this test.
        """
        files_to_process_details = [
            (self.file_pdf1, self.mock_dest_documents), (self.file_docx1, self.mock_dest_documents),
            (self.file_epub1, self.mock_dest_ebooks), (self.file_xlsx1, self.mock_dest_spreadsheets),
            (self.file_csv1, self.mock_dest_data), (self.file_jpg1, self.mock_dest_images),
            (self.file_png1, self.mock_dest_images), (self.file_svg1, self.mock_dest_vectorgraphics),
            (self.file_psd1, self.mock_dest_design_files), (self.file_zip1, self.mock_dest_archives),
            (self.file_exe1, self.mock_dest_executables_installers),
            (self.file_mp3_1, self.mock_dest_music), (self.file_wav1, self.mock_dest_audio),
            (self.file_mp4_1, self.mock_dest_videos), (self.file_log1, self.mock_dest_logfiles),
            (self.file_json1, self.mock_dest_data), (self.file_yaml1, self.mock_dest_configs),
            (self.file_ttf1, self.mock_dest_fonts),
            (self.file_dup_txt_src, self.mock_dest_textfiles), # Included for move count
            (self.file_dup_img_src, self.mock_dest_images),   # Included for move count
        ]
        # In this test, all destination files are new, so no pre-configuration in
        # `self.configured_dest_file_paths` is needed. The generic mocks returned by
        # `_specific_destination_file_division` will have `exists.return_value = False`.

        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            organizer.organize()

        # Verify that category folders were created
        expected_mkdir_target_folders = {details[1] for details in files_to_process_details}
        for folder_mock in expected_mkdir_target_folders:
            folder_mock.mkdir.assert_any_call(parents=True, exist_ok=True)
        
        # Verify that shutil.move was called for each processable file
        self.assertEqual(mock_shutil_move.call_count, len(files_to_process_details))
        expected_move_calls = [
            call(str(file_mock), f"{str(dest_folder_mock)}/{file_mock.name}")
            for file_mock, dest_folder_mock in files_to_process_details
        ]
        mock_shutil_move.assert_has_calls(expected_move_calls, any_order=True)

        # Verify organizer's internal counters
        self.assertEqual(organizer.files_successfully_moved_or_renamed, len(files_to_process_details))
        self.assertEqual(organizer.skipped_identical_duplicates, 0)

    @patch('organizer.shutil.move')
    def test_organize_dry_run_logs_correctly(self, mock_shutil_move: MagicMock):
        """
        Tests the dry-run mode (`dry_run=True`).
        Ensures that:
        - No actual file system changes are made (`shutil.move` is not called).
        - Appropriate log messages ("Would move", "File already exists", "Ignoring file") are generated.
        - The summary log reflects the simulated actions.
        """
        # Configure one destination file to "exist" to test the "already exists" log path
        self._configure_destination_file_mock(
            dest_category_folder_mock=self.mock_dest_textfiles, 
            file_name=self.file_dup_txt_src.name, 
            exists=True, 
            content_hash="hash_for_readme_dup_in_dest_dry_run" # Specific hash for this test
        )

        files_expected_to_be_logged_as_considered = [
            (self.file_pdf1, self.mock_dest_documents), (self.file_docx1, self.mock_dest_documents),
            (self.file_epub1, self.mock_dest_ebooks), (self.file_xlsx1, self.mock_dest_spreadsheets),
            (self.file_csv1, self.mock_dest_data), (self.file_jpg1, self.mock_dest_images),
            (self.file_png1, self.mock_dest_images), (self.file_svg1, self.mock_dest_vectorgraphics),
            (self.file_psd1, self.mock_dest_design_files), (self.file_zip1, self.mock_dest_archives),
            (self.file_exe1, self.mock_dest_executables_installers),
            (self.file_mp3_1, self.mock_dest_music), (self.file_wav1, self.mock_dest_audio),
            (self.file_mp4_1, self.mock_dest_videos), (self.file_log1, self.mock_dest_logfiles),
            (self.file_json1, self.mock_dest_data), (self.file_yaml1, self.mock_dest_configs),
            (self.file_ttf1, self.mock_dest_fonts),
            (self.file_dup_txt_src, self.mock_dest_textfiles), # This one is pre-configured to exist
            (self.file_dup_img_src, self.mock_dest_images),   # This one is not, will be "Would move"
        ]
        files_to_be_ignored_by_rule = [self.file_no_ext, self.file_unmapped_ext]
        
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=True)
        # Dry run still "calculates" hashes for its simulation, so we patch it.
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            with self.assertLogs(logger='organizer', level='DEBUG') as log_context_debug:
                organizer.organize()
        
        mock_shutil_move.assert_not_called() # Crucial for dry-run
        log_output_str = "\n".join(log_context_debug.output)

        # Verify log messages for each considered file
        for file_mock, dest_folder_mock in files_expected_to_be_logged_as_considered:
            expected_dest_path_str = f"{str(dest_folder_mock)}/{file_mock.name}"
            # Check if this specific path was pre-configured to exist
            if expected_dest_path_str in self.configured_dest_file_paths and \
               self.configured_dest_file_paths[expected_dest_path_str].exists.return_value:
                 self.assertIn(f"[DRY RUN] File '{file_mock.name}' already exists at '{str(dest_folder_mock)}'.", log_output_str)
            else:
                self.assertIn(f"[DRY RUN] Would move '{file_mock.name}' to '{expected_dest_path_str}'", log_output_str)

        # Verify log messages for ignored files
        self.assertIn(f"Ignoring file '{self.file_no_ext.name}' (reason: no extension)", log_output_str)
        self.assertIn(f"Ignoring file '{self.file_unmapped_ext.name}' (reason: extension '{self.file_unmapped_ext.suffix}' not in EXTENSION_MAP)", log_output_str)
        
        # Verify summary log messages
        total_scanned = len(self.all_source_files_for_setup)
        num_ignored = len(files_to_be_ignored_by_rule)
        num_considered = len(files_expected_to_be_logged_as_considered)
        self.assertIn(f"Total files scanned: {total_scanned}", log_output_str)
        self.assertIn(f"Files ignored by extension rules: {num_ignored}", log_output_str)
        self.assertIn(f"Files that would be considered for moving/renaming: {num_considered}", log_output_str)

    @patch('organizer.shutil.move')
    def test_organize_deduplication_skips_identical_file(self, mock_shutil_move: MagicMock):
        """
        Tests deduplication: an identical file (same name, same hash)
        already exists in the destination. The source file should be skipped.
        """
        self.mock_source_dir.rglob.return_value = [self.file_dup_txt_src] # Source hash: "same_hash_for_txt_dup"
        
        # Configure the destination file to exist with the SAME hash
        self._configure_destination_file_mock(
            dest_category_folder_mock=self.mock_dest_textfiles,
            file_name=self.file_dup_txt_src.name,
            exists=True,
            content_hash="same_hash_for_txt_dup" # Identical hash
        )

        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            with self.assertLogs(logger='organizer', level='INFO') as log_context:
                organizer.organize()

        mock_shutil_move.assert_not_called() # File should not be moved
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 1)
        log_output_str = "\n".join(log_context.output)
        self.assertIn(f"Skipping identical file (same name '{self.file_dup_txt_src.name}', same hash)", log_output_str)

    @patch('organizer.shutil.move')
    def test_organize_deduplication_renames_conflicting_file(self, mock_shutil_move:MagicMock):
        """
        Tests deduplication: a file with the same name but DIFFERENT content (hash)
        exists in the destination. The source file should be renamed and moved.
        """
        self.mock_source_dir.rglob.return_value = [self.file_dup_img_src] # Source hash: "image_hash_source_A"

        # Configure the destination file to exist with a DIFFERENT hash
        self._configure_destination_file_mock(
            dest_category_folder_mock=self.mock_dest_images,
            file_name=self.file_dup_img_src.name, # Same name as source
            exists=True,
            content_hash="image_hash_dest_B_different" # Different hash
        )
        # The renamed file (e.g., "photo_dup(1).png") is NOT pre-configured.
        # This allows `_get_unique_destination_path` to find it as non-existent,
        # as `_specific_destination_file_division` will return a generic mock
        # with `exists.return_value = False` for it.
        
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            with self.assertLogs(logger='organizer', level='INFO') as log_context:
                organizer.organize()

        # Construct the expected renamed path
        base_name_stem = Path(self.file_dup_img_src.name).stem
        base_name_suffix = Path(self.file_dup_img_src.name).suffix
        renamed_file_name = f"{base_name_stem}(1){base_name_suffix}"
        expected_renamed_path_str = f"{self.mock_dest_images}/{renamed_file_name}"
        
        mock_shutil_move.assert_called_with(str(self.file_dup_img_src), expected_renamed_path_str)
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 1)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)
        log_output_str = "\n".join(log_context.output)
        self.assertIn(f"File '{self.file_dup_img_src.name}' exists at '{str(self.mock_dest_images)}' but with different content", log_output_str)
        self.assertIn(f"Moving (renamed) '{self.file_dup_img_src.name}' to '{expected_renamed_path_str}'", log_output_str)

    @patch('organizer.shutil.move', side_effect=Exception("Simulated Shutil Error during actual move operation"))
    def test_organize_handles_shutil_move_error(self, mock_shutil_move_with_error: MagicMock):
        """
        Tests that `FileOrganizer` correctly handles errors (e.g., `shutil.Error`, `OSError`)
        that occur during the `shutil.move` operation.
        The error should be logged, and the file not counted as moved.
        """
        self.mock_source_dir.rglob.return_value = [self.file_pdf1]
        # For this test, the destination file does not exist, so no hash comparison logic is triggered.
        # The error occurs directly during the move attempt.
        
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            with self.assertLogs(logger='organizer', level='ERROR') as log_context:
                organizer.organize()

        expected_dest_path_str = f"{self.mock_dest_documents}/{self.file_pdf1.name}"
        mock_shutil_move_with_error.assert_called_once_with(str(self.file_pdf1), expected_dest_path_str)
        
        log_output_str = "\n".join(log_context.output)
        # The organizer.py catches generic Exception and logs "Unexpected error"
        self.assertIn(f"Unexpected error moving file '{self.file_pdf1.name}' to '{expected_dest_path_str}'", log_output_str)
        self.assertIn("Simulated Shutil Error during actual move operation", log_output_str) # Check for the original error message
        
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)

    @patch('organizer.shutil.move')
    def test_organize_skips_file_on_source_hash_calculation_error(self, mock_shutil_move: MagicMock):
        """
        Tests behavior when hash calculation for a SOURCE file fails.
        The file should be skipped, an error logged, and no move attempted.
        """
        self.mock_source_dir.rglob.return_value = [self.file_pdf1]
        self.file_pdf1.mocked_content_hash = None # Simulate hash calculation error for this source file

        # Configure a destination file to "exist" to force entry into the hash comparison logic.
        # The actual hash of this destination file doesn't matter as the source hash error occurs first.
        self._configure_destination_file_mock(
            dest_category_folder_mock=self.mock_dest_documents,
            file_name=self.file_pdf1.name,
            exists=True,
            content_hash="dummy_dest_hash_when_source_fails" 
        )
        
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect) as mock_calc_hash_method:
            with self.assertLogs(logger='organizer', level='ERROR') as log_context:
                organizer.organize()

        # Verify _calculate_file_hash was called for the source file
        source_call_made = any(call_args[0][0] is self.file_pdf1 for call_args in mock_calc_hash_method.call_args_list)
        self.assertTrue(source_call_made, "_calculate_file_hash not called for the source file.")
        
        mock_shutil_move.assert_not_called() # File should not be moved
        self.assertIn(f"Skipping '{self.file_pdf1.name}' due to error calculating its hash.", "\n".join(log_context.output))
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)


    @patch('organizer.shutil.move')
    def test_organize_skips_file_on_destination_hash_calculation_error_when_conflict(self, mock_shutil_move: MagicMock):
        """
        Tests behavior when a filename conflict exists, and hash calculation
        for the existing DESTINATION file fails.
        The source file should be skipped, and an error logged.
        """
        self.mock_source_dir.rglob.return_value = [self.file_pdf1]
        self.file_pdf1.mocked_content_hash = "valid_source_hash_pdf1" # Source file has a valid hash

        # Configure the destination file to "exist" but have its hash calculation "fail" (return None)
        configured_dest_mock = self._configure_destination_file_mock(
            dest_category_folder_mock=self.mock_dest_documents,
            file_name=self.file_pdf1.name, # Same name, causing conflict
            exists=True,
            content_hash=None # Simulate hash calculation error for this destination file
        )

        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect) as mock_calc_hash_method:
            with self.assertLogs(logger='organizer', level='ERROR') as log_context:
                organizer.organize()
        
        # Verify _calculate_file_hash was called for both source and the (problematic) destination
        source_call_made = any(call_args[0][0] is self.file_pdf1 for call_args in mock_calc_hash_method.call_args_list)
        dest_call_made = any(call_args[0][0] is configured_dest_mock for call_args in mock_calc_hash_method.call_args_list)

        self.assertTrue(source_call_made, "_calculate_file_hash not called for the source file.")
        self.assertTrue(dest_call_made, "_calculate_file_hash not called for the pre-configured destination file.")
        
        mock_shutil_move.assert_not_called() # File should not be moved
        log_output_str = "\n".join(log_context.output)
        # Ensure the log message matches what organizer.py produces (using .name for the destination file)
        self.assertIn(f"Skipping '{self.file_pdf1.name}'. Could not calculate hash for existing destination file '{configured_dest_mock.name}'.", log_output_str)
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)


if __name__=='__main__':
    # To see DEBUG logs and test-specific prints during test runs, uncomment the following lines:
    # import sys
    # logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # logger.setLevel(logging.DEBUG) # Ensure the 'organizer' logger itself is also set to DEBUG
    unittest.main(verbosity=2)

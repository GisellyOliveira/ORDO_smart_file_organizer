import unittest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import shutil

from .base_test import BaseOrganizerTest
from organizer import FileOrganizer, DEFAULT_EXTENSION_MAP

class TestCoreLogicAndInitialization(BaseOrganizerTest):
    """
    Tests for the core file organization logic and initialization of FileOrganizer.
    """

    def setUp(self):
        """
        Call super().setUp() to get all the common mocks from BaseOrganizerTest.
        """
        super().setUp()
    

    # --- Startup Tests ---
    
    def test_initialization_success(self):
        """Tests successful initialization of FileOrganizer with valid parameters."""
        # Mock the configuration methods called in __init__
        mock_config_path = MagicMock(spec=Path, name="MockConfigPathForInit")
        mock_config_path.__str__.return_value = "/fake/config.organizer_config.json" # For the logs

        # When instantiating FileOrganizer, _get_config_file_path and _load_extension_map_config are called.
        # It's necessary to mock these to isolate the __init__ test.
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path) as mock_get_path, \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()) as mock_load_map:

            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        
        # Check if the mocks of the config methods were called (occurs in __init__)
        mock_get_path.assert_called_once()
        mock_load_map.assert_called_once()

        self.assertEqual(organizer.source_dir, self.mock_source_dir)
        self.assertEqual(organizer.dest_dir, self.mock_dest_dir)
        self.assertFalse(organizer.dry_run, "dry_run should be False by default.")
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)

        # New assertions for configuration-related attributes
        self.assertEqual(organizer.config_path, mock_config_path)
        self.assertEqual(organizer.session_extension_map, DEFAULT_EXTENSION_MAP)
        self.assertFalse(organizer._map_changed_this_session)


    def test_initialization_with_dry_run_true(self):
        """Tests successful initialization with dry-run set to True.""" 
        mock_config_path = MagicMock(spec=Path, name="MockConfigPathDryRun")
        mock_config_path.__str__.return_value = "/fake/config_dry.json"

        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):

            organizer = FileOrganizer(self.mock_source_dir, self. mock_dest_dir, dry_run=True)
        
        self.assertTrue(organizer.dry_run)
        self.assertEqual(organizer.source_dir, self.mock_source_dir)
        self.assertEqual(organizer.dest_dir, self.mock_dest_dir)
    

    def test_init_invalid_source_dir_raises_valueerror(self):
        """Tests FileOrganizer initialization with a non-existent/invalid source directory."""
        self.mock_source_dir.is_dir.return_value = False # Simulates that the source is not a directory

        expected_regex = f"Source directory does not exist or is not a directory: {str(self.mock_source_dir)}"

        # No need to test config methods here because __init__ must fail before calling them.
        with self.assertRaisesRegex(ValueError, expected_regex):
            FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
    

    def test_init_dest_is_file_raises_valueerror(self):
        """Tests FileOrganizer initialization when destination path exists but is a file."""
        self.mock_dest_dir.exists.return_value = True # Destiny exists
        self.mock_dest_dir.is_dir.return_value = False # But it's not a directory but a file

        # __init__ mist fail before calling config's methods
        with self.assertRaisesRegex(ValueError, "Destination path exists but is not a directory"):
            FileOrganizer(self.mock_source_dir, self.mock_dest_dir)


    # --- Tests for File Organization Logic ---
    @patch('organizer.shutil.move') # Verifies if the file was moved
    @patch('builtins.input') # For the interactive part of new extensions
    @patch.object(FileOrganizer, '_interactive_edit_existing_mappings') # To skip interactive editing
    @patch.object(FileOrganizer, '_save_extension_map_config') # To skip savings
    def test_organize_moves_single_mapped_file_correctly(
        self,
        mock_save_config: MagicMock,
        mock_interactive_edit: MagicMock,
        mock_input: MagicMock,
        mock_shutil_move: MagicMock
    ):
        """
        Tests that a single file with a mapped extension is moved to the correct category.
        """
        # 1. Set up mock_input for the "new extensions" phase
        # For this test, we don't want any new extensions to be mapped.
        # If the test file has a known extension, the prompt won't even appear for it.
        # If there are unknown extensions (from the other files in self.all_source_files_for_setup),
        # make the input return '' (ignore).
        mock_input.return_value = '' # Ignores any prompt for new extensions

        # # 2. Configure FileOrganizer
        # _get_config_file_path and _load_extension_map_config are already mocked
        # in __init__ for initialization tests. For `organize` tests,
        # we want to explicitly control session_extension_map.
        mock_config_path = MagicMock(spec=Path, name="MockConfigPathOrganize")

        # Instantiate with a specific session map (the default in this case)
        # This ensures that we know which map is in use.
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()) as mock_load_map_init:
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
            # Makes sure that the session map is what we expect before organizing it
            organizer.session_extension_map = DEFAULT_EXTENSION_MAP.copy()

        # 3. Set the source file for this test
        # We'll use self.file_pdf1 from the BaseOrganizerTest setUp
        # and expect it to go into self.category_folder_mocks["Documents"]
        # (p.s.: self.mock_dest_documents is now created dynamically in BaseOrganizerTest)

        # Set up self.mock_source_dir.rglob to return only the file we want to test
        self.mock_source_dir.rglob.return_value = [self.file_pdf1]

        # 4. Mocking _calculate_file_hash (already done in BaseOrganizerTest via self._mock_calculate_hash_side_effect)
        # and make sure it is applied
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            organizer.organize() # Runs the organization
        
        # 5. Assertions
        # Check if _interactive_edit_existing_mappings was called (as it should have been)
        mock_interactive_edit.assert_called_once()

        # Checks if shutil.move was called correctly
        expected_dest_folder_mock = self.category_folder_mocks["Documents"] # Accesses the dynamic mock
        expected_dest_path_str = f"{str(expected_dest_folder_mock)}/{self.file_pdf1.name}"
        mock_shutil_move.assert_called_once_with(str(self.file_pdf1), expected_dest_path_str)

        # Checks if destiny folder was created
        expected_dest_folder_mock.mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Checks counters
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 1)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)

        # Checks if _save_extension_map_config was called (it should have been)
        mock_save_config.assert_called_once()
    

    @patch('organizer.shutil.move')
    @patch('builtins.input', return_value='') # Ignores any prompt for new extensions
    @patch.object(FileOrganizer, '_interactive_edit_existing_mappings')
    @patch.object(FileOrganizer, '_save_extension_map_config')
    def test_organize_ignores_file_with_no_extension(
        self,
        mock_save_config: MagicMock,
        mock_interactive_edit: MagicMock,
        mock_input: MagicMock,
        mock_shutil_move: MagicMock
    ):
        """
        Tests that a file with no extension is ignored and not moved.
        """
        #1. Configure FileOrganizer with mocks for configuration and interactivity
        mock_config_path = MagicMock(spec=Path, name="MockConfigPathNoExt")
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
            organizer.session_extension_map = DEFAULT_EXTENSION_MAP.copy() # It secures the map
        
        # 2. Set the source file for this test (without extension)
        self.mock_source_dir.rglob.return_value = [self.file_no_ext] # BaseOrganizerTest self.file_no_ext

        # 3. It runs organize (calculate_hash should not be called for early skipped files)
        # We don't need to mock _calculate_file_hash here, as it shouldn't be reachable.
        with self.assertLogs(self.logger, level='DEBUG') as log_context: # DEBUG to observe "Ignoring file"
            organizer.organize()
        
        # 4. Assertions
        mock_interactive_edit.assert_called_once() # Its called at the beginning of organize()
        mock_shutil_move.assert_not_called() # SHOULD NOT be moved

        # Category folders should NOT be created
        # (hard to check directly without iterating over all folder mocks,
        # but if move was not called, mkdir on the category should not have been either)

        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)

        # It checks the specific ignore log
        self.assertIn(f"Ignoring file '{self.file_no_ext.name}' (reason: no extension)", "\n".join(log_context.output))

        mock_save_config.assert_called_once()
    

    @patch('organizer.shutil.move')
    @patch('builtins.input', return_value='') # It ignores any prompt for new extensions
    @patch.object(FileOrganizer, '_interactive_edit_existing_mappings')
    @patch.object(FileOrganizer, '_save_extension_map_config')
    def test_organize_ignores_file_with_unmapped_extension(
        self,
        mock_save_config: MagicMock,
        mock_interactive_edit: MagicMock,
        mock_input: MagicMock,
        mock_shutil_move: MagicMock
    ):
        """ 
        Tests that a file with an unmapped extension is ignored and not moved.
        """
        # 1. Configuring FileOrganizer
        mock_config_path = MagicMock(spec=Path, name="MockConfigPathUnmappedExt")

        # Using a session map that DEFINITELY does not have '.dat'
        # The DEFAULT_EXTENSION_MAP no longer does, but to be explicit:
        current_test_map = DEFAULT_EXTENSION_MAP.copy()
        if '.dat' in current_test_map: # If the pattern changes in the future
            del current_test_map['.dat']
        
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=current_test_map): # It uses the clean map
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
            # Explicitly assigns it to ensure that _interactive_edit_existing_mappings (mock) does not change it
            organizer.session_extension_map = current_test_map
        
        # 2. Sets the source file for this test (.dat extension not mapped)
            self.mock_source_dir.rglob.return_value = [self.file_unmapped_ext]

        # 3. Running organize
        with self.assertLogs(self.logger, level='DEBUG') as log_context:
            organizer.organize()
        
        # 4. Assertions
        mock_interactive_edit.assert_called_once()
        mock_shutil_move.assert_not_called()
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)

        self.assertIn(f"Ignoring file '{self.file_unmapped_ext.name}' (reason: extension '{self.file_unmapped_ext.suffix}' not in current session's extension map)", "\n".join(log_context.output))

        mock_save_config.assert_called_once()
    

    @patch('organizer.shutil.move')
    @patch('builtins.input', return_value='')
    @patch.object(FileOrganizer, '_interactive_edit_existing_mappings')
    @patch.object(FileOrganizer, '_save_extension_map_config')
    def test_deduplication_skips_identical_file(
        self,
        mock_save_config: MagicMock,
        mock_interactive_edit: MagicMock,
        mock_input: MagicMock,
        mock_shutil_move: MagicMock
    ):
        """ 
        Tests that if an identical file (same name, same hash) exists at the 
        destination, the source file is skipped.
        """
        # 1. Configuring FileOrganizer
        mock_config_path = MagicMock(spec=Path, name="MockConfigPathSkipDup")
        # Using DEFAULT_EXTENSION_MAP for this test
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
            organizer.session_extension_map = DEFAULT_EXTENSION_MAP.copy()
        
        # 2. It sets the source file for this test
        # self.file_dup_txt_src hash "same_hash_for_txt_dup"
        self.mock_source_dir.rglob.return_value = [self.file_dup_txt_src]

        # 3. It sets the target file to ALREADY EXIST with the SAME HASH
        # and gets the target folder mock for .txt (TextFiles)
        dest_textfiles_folder_mock = self.category_folder_mocks["TextFiles"]
        self._configure_destination_file_mock(
            dest_category_folder_mock=dest_textfiles_folder_mock,
            file_name=self.file_dup_txt_src.name, # Same name
            exists=True,
            content_hash="same_hash_for_txt_dup"
        )

        # 4. Mocking _calculate_file_hash (already done via self._mock_calculate_hash_side_effect)
        # and running organize
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            # We expect INFO logs for "Skipping identical file" and DEBUG for the comparison
            with self.assertLogs(self.logger, level='DEBUG') as log_context: # Using DEBUG to see "Comparing hashes..."
                organizer.organize()
        
        # 5. Assertions
        mock_interactive_edit.assert_called_once()
        mock_shutil_move.assert_not_called()

        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 1) # 1 file skipped

        log_output_str = "\n".join(log_context.output)
        self.assertIn(f"File '{self.file_dup_txt_src.name}' already exists at '{str(dest_textfiles_folder_mock)}'. Comparing hashes...", log_output_str)
        self.assertIn(f"Skipping identical file (same name '{self.file_dup_txt_src.name}', same hash)", log_output_str)

        mock_save_config.assert_called_once()


    @patch('organizer.shutil.move')
    @patch('builtins.input', return_value='') # Ignore new extensions
    @patch.object(FileOrganizer, '_interactive_edit_existing_mappings')
    @patch.object(FileOrganizer, '_save_extension_map_config')
    def test_deduplication_renames_conflicting_file(
        self,
        mock_save_config: MagicMock,
        mock_interactive_edit: MagicMock,
        mock_input: MagicMock,
        mock_shutil_move: MagicMock
    ):
        """
        Tests that if with the same name but different content (hash)
        exists at the destination, the source file is renamed and moved.
        """
        # 1. Configuring FileOrganizer
        mock_config_path = MagicMock(spec=Path, name="MockConfigPathRenameDup")
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
            organizer.session_extension_map = DEFAULT_EXTENSION_MAP.copy()
        
        # 2. Defining the source file for this test
        # self.file_dup_img_src has name "photo_dup.png" and hash "image_hash_source_A
        self.mock_source_dir.rglob.return_value = [self.file_dup_img_src]

        # 3. Setting the target file to ALREADY EXIST with the SAME NAME but DIFFERENT HASH
        dest_images_folder_mock = self.category_folder_mocks["Images"] #.png files go to Images folder

        # Mock to original file in destination (photo_dup.png)
        self._configure_destination_file_mock(
            dest_category_folder_mock=dest_images_folder_mock,
            file_name=self.file_dup_img_src.name, # Same name
            exists=True,
            content_hash="image_hash_DEST_B_DIFFERENT" # Different hash!
        )

        # 4. Mocking _calculate_file_hash and executing organize
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            with self.assertLogs(self.logger, level='DEBUG') as log_context: # DEBUG for "Comparing hashes..."
                organizer.organize()
        
        # Assertions:
        mock_interactive_edit.assert_called_once()
        
        # Building the expected name for the renamed file
        source_file_path_obj = Path(self.file_dup_img_src.name) # Using pathlib to extract stem/suffix
        renamed_file_name = f"{source_file_path_obj.stem}(1){source_file_path_obj.suffix}"
        expected_renamed_dest_path_str = f"{str(dest_images_folder_mock)}/{renamed_file_name}"

        mock_shutil_move.assert_called_once_with(str(self.file_dup_img_src), expected_renamed_dest_path_str)

        # The destination folder named "Images" must be created
        dest_images_folder_mock.mkdir.assert_called_once_with(parents=True, exist_ok=True)

        self.assertEqual(organizer.files_successfully_moved_or_renamed, 1) # One file moved (renamed)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)

        log_output_str = "\n".join(log_context.output)
        self.assertIn(f"File '{self.file_dup_img_src.name}' exists at '{str(dest_images_folder_mock)}' but with different content (hashes differ). Renaming source before move.", log_output_str)
        self.assertIn(f"Moving (renamed) '{self.file_dup_img_src.name}' to '{expected_renamed_dest_path_str}'", log_output_str)
        self.assertIn(f"Successfully moved '{self.file_dup_img_src.name}' to '{expected_renamed_dest_path_str}'", log_output_str)

        mock_save_config.assert_called_once()
    

    @patch('organizer.shutil.move')
    @patch('builtins.input', return_value='') # Ignore new extensions
    @patch.object(FileOrganizer, '_interactive_edit_existing_mappings')
    def test_dry_run_simulates_actions_and_logs_correctly(
        self,
        mock_interactive_edit: MagicMock,
        mock_input: MagicMock,
        mock_shutil_move: MagicMock
    ):
        """
        Tests that in dry_run mode:
        - No files are actually moved.
        _ Appropriate "[DRY RUN]" log messages are generated for simulated actions,
        including moving new files and handling pre-existing files (simulated).
        """
        # 1. Configuring FileOrganizer for dry_run=True
        mock_config_path = MagicMock(spec=Path, name="MockConfigPathDryRunLogic")
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=True) # IMPORTANT: dry_run=True
            organizer.session_extension_map = DEFAULT_EXTENSION_MAP.copy()
        
        # 2. Configuring source and destination file scenarios
        # - A file that would normally be moved (file_pdf1)
        # - A file that already exists in the destination (file_dup_txt_src) to simulate hash comparison
        # - A file that has no extension (file_no_ext) to be ignored
        # File that already exists in the destination (to simulate "already exists" logic)
        dest_textfiles_folder_mock = self.category_folder_mocks["TextFiles"]
        self._configure_destination_file_mock(
            dest_category_folder_mock=dest_textfiles_folder_mock,
            file_name=self.file_dup_txt_src.name, # readme_dup.txt
            exists=True, # Simulates it already exists
            content_hash="hash_does_not_matter_for_dry_run_exists_check" # Hash is not compared in dry run if it only checks for existence
        )

        # List of files that rglob will return:
        # self.file_pdf1 -> should log "Would move"
        # self.file_dup_txt_src -> should log "File ... already exists ... Would compare hashes"
        # self.file_no_ext -> should log "Ignoring file"
        self.mock_source_dir.rglob.return_value = [
            self.file_pdf1,
            self.file_dup_txt_src,
            self.file_no_ext
        ]

        # The _move_file_with_deduplication method in dry_run just logs, it doesn't call _calculate_file_hash.
        # So this patch is more to make sure that if it were called, it wouldn't break.
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            with self.assertLogs(self.logger, level='DEBUG') as log_context:
                organizer.organize()
        
        # 4. Assertions:
        mock_interactive_edit.assert_called_once()
        mock_shutil_move.assert_not_called() # No file should be moved in dry run

        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)

        log_output_str = "\n".join(log_context.output)

        # Checks logs for file_pdf1 (should be moved)
        expected_dest_pdf_folder = self.category_folder_mocks["Documents"]
        expected_full_dest_path_pdf = f"{str(expected_dest_pdf_folder)}/{self.file_pdf1.name}"
        self.assertIn(f"[DRY RUN] Would move '{self.file_pdf1.name}' to '{expected_full_dest_path_pdf}'", log_output_str)

        dest_textfiles_folder_mock = self.category_folder_mocks["TextFiles"]

        # Checks logs for file_dup_txt_src (already exists at the destination)
        self.assertIn(f"[DRY RUN] File '{self.file_dup_txt_src.name}' already exists at '{str(dest_textfiles_folder_mock)}'. Would compare hashes", log_output_str)

        # Check logs for file_no_ext (ignored) - DEBUG log
        # Since we capture both INFO and DEBUG (by changing the logger level), we can check
        self.assertIn(f"Ignoring file '{self.file_no_ext.name}' (reason: no extension)", log_output_str)

        # Checks the summary log
        self.assertIn("--- Dry run finished. ---", log_output_str)
        self.assertIn("Total files scanned (during organization pass): 3", log_output_str) # file_no_ext
        self.assertIn("Files that would be considered for moving/renaming: 2", log_output_str) # pdf, dup_txt
        self.assertIn("In dry run, duplicate checks and renaming are simulated and logged per file.", log_output_str)

        self.assertIn("No changes made to extension mappings this session. Nothing to save.", log_output_str)
    

    @patch('organizer.shutil.move', side_effect=shutil.Error("Simulated Shutil Disk Full Error"))
    @patch('builtins.input', return_value='')
    @patch.object(FileOrganizer, '_interactive_edit_existing_mappings')
    @patch.object(FileOrganizer, '_save_extension_map_config')
    def test_shutil_move_error_handling(
        self,
        mock_save_config: MagicMock,
        mock_interactive_edit: MagicMock,
        mock_input: MagicMock,
        mock_shutil_move_with_error: MagicMock
    ):
        """
        Tests that FileOrganizer correctly handles an error (e.g., shutil.Error)
        that occurs during the shutil.move operation.
        The error should be logged, and the file not counted as moved.
        """
        # 1. Configuring FileOrganizer
        mock_config_path = MagicMock(spec=Path, name="MockConfigPathShutilError}")
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
            organizer.session_extension_map = DEFAULT_EXTENSION_MAP.copy()
        
        # 2. Sets the source file for this test (a file that would normally be moved)
        # self.file_pdf1 from BaseOrganizerTest
        self.mock_source_dir.rglob.return_value = [self.file_pdf1]

        # 3. The destination does not need to exist, the error will occur on 'move'
        # _calculate_file_hash will be called, so it needs to be mocked.

        # 4. Run organize and capture ERROR logs
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            # The shutil error is caught and logged as ERROR by _move_file_with_deduplication
            with self.assertLogs(self.logger, level='ERROR') as log_context:
                organizer.organize()
        
        # 5. Assertions:
        mock_interactive_edit.assert_called_once()

        # Checks if shutil.move was called (even if it raised an error)
        expected_dest_folder_mock = self.category_folder_mocks["Documents"]
        expected_dest_path_str = f"{str(expected_dest_folder_mock)}/{self.file_pdf1.name}"
        mock_shutil_move_with_error.assert_called_once_with(str(self.file_pdf1), expected_dest_path_str)

        expected_dest_folder_mock.mkdir.assert_called_once_with(parents=True, exist_ok=True)

        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0) # it wasn't successfully moved
        self.assertEqual(organizer.skipped_identical_duplicates, 0)

        log_output_str = "\n".join(log_context.output)

        self.assertIn(f"Shutil Error moving file '{self.file_pdf1.name}' to '{expected_dest_path_str}'", log_output_str)
        self.assertIn("Simulated Shutil Disk Full Error", log_output_str)

        mock_save_config.assert_called_once()

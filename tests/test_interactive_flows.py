# Testes específicos para:
#   ### _interactive_edit_existing_mappings() (mockando input).
#   ### A seção de mapeamento de novas extensões dentro do método organize() (mockando input).
import unittest
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from .base_test import BaseOrganizerTest
from organizer import FileOrganizer, DEFAULT_EXTENSION_MAP

class TestInteractiveFlows(BaseOrganizerTest):
    """
    Tests the interactive conversation flows of the FileOrganizer,
    simulating user input and verifying the application's state and responses.
    """

    def setUp(self):
        """
        Calls super().setUp() to get all the common mocks.
        """
        super().setUp()
    
    # --- Testing for the mapping flow of new extensions ---
    
    @patch('organizer.shutil.move')
    @patch('builtins.input')
    def test_new_unmapped_extension_is_mapped_by_user(self, mock_input: MagicMock, mock_shutil_move: MagicMock):
        """ 
        Scenario: Script finds a new extension ('.dat') and asks the user.
        User responds with a folder name ('DataFiles').
        Verify: Session extension map is updated correctly.
        """
        # Arrange
        # Configures FileOrganizer for a real test (not dry-run)
        # Mocking __init__ to isolate the test from the logic of loading real config files
        mock_config_path = MagicMock(spec=Path)
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
            # It ensures that the '.dat' extension is not in the initial map
            organizer.session_extension_map.pop('.dat', None)
        
        # Focusing the test on a single file: the one with not mapped extension
        self.mock_source_dir.rglob.return_value = [self.file_unmapped_ext]

        user_responses = [
            'n', # Reply to "Review or modify current extension mappings? (yes/No)"
            'CustomDataFiles', # Reply to new '.dat' extension prompt
            'n' # Reply to "Save current extension mappings for future use? (yes/No)"
        ]
        mock_input.side_effect = user_responses

        expected_new_folder_name = 'CustomDataFiles'

        # Running the organize() method and capturing the logs for verification
        with self.assertLogs(self.logger, level='INFO') as log_context:
            organizer.organize()
        
        # Assertions
        # 1. Was the organizer's internal state updated correctly?
        self.assertTrue(organizer._map_changed_this_session, "The map change flag should be True.")
        self.assertIn('.dat', organizer.session_extension_map)
        self.assertEqual(organizer.session_extension_map['.dat'], expected_new_folder_name)

        # 2. Did the script communicate the change correctly to the user?
        log_output = "\n".join(log_context.output)
        self.assertIn(f"Extension '.dat' will be organized into folder: '{expected_new_folder_name}'", log_output)

        # 3. Was the file moved to the correct location?
        # The mocking system in base_test creates folder mocks dynamically.
        expected_dest_folder_mock = self.mock_dest_dir / expected_new_folder_name
        expected_dest_path_str = f"{str(expected_dest_folder_mock)}/{self.file_unmapped_ext.name}"

        mock_shutil_move.assert_called_once_with(str(self.file_unmapped_ext), expected_dest_path_str)
        expected_dest_folder_mock.mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # 4. Are the counters correct?
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 1)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)

        # 5. Did the interaction with 'input' go as expected?
        self.assertEqual(mock_input.call_count, 3, "Input deveria ter sido chamado 3 vezes.")
    

    @patch('organizer.shutil.move')
    @patch('builtins.input')
    def test_new_unmapped_extension_is_ignored_by_user(self, mock_input: MagicMock, mock_shutil_move: MagicMock):
        """ 
        Scenario: Script finds '.dat' extension (not mapped).
        User responds with an empty string (presses Enter), to ignore.
        Checks: Map is NOT updated, file is NOT moved and no changes are recorded.
        """
        # --- ARRANGE ---
        # Setting FileOrganizer
        mock_config_path = MagicMock(spec=Path)
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
            organizer.session_extension_map.pop('.dat', None)
        
        self.mock_source_dir.rglob.return_value = [self.file_unmapped_ext]

        user_responses = [
            'n', # Reply to "Review or modify...?"
            '' # Reply to new '.dat' extension prompt (Enter)
        ]
        mock_input.side_effect = user_responses

        with self.assertLogs(self.logger, level='DEBUG') as log_context:
            organizer.organize()
        
        # Assertions
        # 1. The internal state of the organizer must NOT have changed.
        self.assertFalse(organizer._map_changed_this_session, "The map change flag should be False.")
        self.assertNotIn('.dat', organizer.session_extension_map, "The '.dat' extension should not have been added to the map.")

        # 2. The script communicated the decision to ignore.
        log_output = "\n".join(log_context.output)
        self.assertIn("Extension '.dat' will be IGNORED for this session.", log_output)
        self.assertIn("Ignoring file 'backup.dat' (reason: extension '.dat' not in current session's extension map).", log_output)

        # 3. NO FILE should have been moved.
        mock_shutil_move.assert_not_called()

        # 4. Counters must be reset.
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)

        # 5. Interaction with 'input' happened as expected.
        self.assertEqual(mock_input.call_count, 2, "Input should have been called twice.")
    

    @patch('organizer.shutil.move')
    @patch('builtins.input')
    def test_user_provides_invalid_then_valid_folder_name(self, mock_input: MagicMock, mock_shutil_move: MagicMock):
        """
        Scenario: Script finds '.dat' extension. User types an invalid name,
        is warned, and then types a valid name.
        Verify: The warning is logged, the input is prompted again, and the logic
        continues with the valid name.
        """
        # --- ARRANGE ---
        # Setting FileOrganizer
        mock_config_path = MagicMock(spec=Path)
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
            organizer.session_extension_map.pop('.dat', None)
        
        self.mock_source_dir.rglob.return_value = [self.file_unmapped_ext]

        # User response string now includes an error
        invalid_name = "inv/alid"
        valid_name = "MyValidFolder"
        user_responses = [
            'n', # Reply to "Review or modify...?"
            invalid_name, # 1st (invalid) attempt for '.dat' prompt
            valid_name, # 2nd (valid) attempt for '.dat' prompt
            'n' # Reply to "Save current extension
        ]
        mock_input.side_effect = user_responses

        with self.assertLogs(self.logger, level='INFO') as log_context:
            organizer.organize()
        
        # Assertions
        # 1. The internal state was updated with the value VALID.
        self.assertTrue(organizer._map_changed_this_session)
        self.assertEqual(organizer.session_extension_map['.dat'], valid_name)

        # 2. The script reported both error and success.
        log_output = "\n".join(log_context.output)
        self.assertIn(f"Invalid folder name: '{invalid_name}'", log_output)
        self.assertIn(f"Extension '.dat' will be organized into folder: '{valid_name}'", log_output)

        # 3. The file has been moved to the VALID folder.
        expected_dest_folder_mock = self.mock_dest_dir / valid_name
        expected_dest_path_str = f"{str(expected_dest_folder_mock)}/{self.file_unmapped_ext.name}"
        mock_shutil_move.assert_called_once_with(str(self.file_unmapped_ext), expected_dest_path_str)

        # 4. The interaction with 'input' happened the correct number of times (proving the loop).
        # 1(review) + 1(invalid) + 1(valid) + 1(save) = 4 calls
        self.assertEqual(mock_input.call_count, 4)
    

    @patch('builtins.input')
    def test_edit_existing_mapping_flow(self, mock_input: MagicMock):
        """
        Scenario: User decides to review mappings, enters edit mode
        and changes the target from '.pdf' extension to 'PDF_Files'.
        Verify: Session map is updated with the new value.
        """

        # --- Arrange ---
        mock_config_path = MagicMock(spec=Path)
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        
        # Checking the initial state just to make sure
        initial_folder = organizer.session_extension_map['.pdf']
        self.assertEqual(initial_folder, "Documents")

        # Simulating users input
        expected_new_folder = 'PDF_Files'
        user_responses = [
            'y', # Reply to "Review or modify...?"
            '.pdf', # Reply to "Enter extension to modify..."
            expected_new_folder, # Reply to "New folder..." -> The new name of the folder.
            'done' # Reply to "Enter extension to modify..." -> Exit the loop.
        ]
        mock_input.side_effect = user_responses

        # Directly calling the method we want to test
        with self.assertLogs(self.logger, level='INFO') as log_context:
            organizer._interactive_edit_existing_mappings()
        
        # Assertions
        # 1. The internal state of the organizer has been updated correctly.
        self.assertTrue(organizer._map_changed_this_session, "The change flag should be True.")
        self.assertEqual(organizer.session_extension_map['.pdf'], expected_new_folder)

        # 2. The script communicated the change to the user.
        log_output = "\n".join(log_context.output)
        self.assertIn(f"Mapping for '.pdf' changed from '{initial_folder}' to '{expected_new_folder}'.", log_output)

        # 3. Interaction with the 'input' happened as expected.
        self.assertEqual(mock_input.call_count, 4)
    

    @patch('builtins.input')
    def test_remove_existing_mapping_flow(self, mock_input: MagicMock):
        """
        Scenario: User decides to review the mappings and uses the keyword 'ignore'
        to remove the mapping of the '.txt' extension.
        Verify: The '.txt' extension is removed from the session map.
        """
        # --- Arrange ---
        # Sets up a clean instance of the organizer
        mock_config_path = MagicMock(spec=Path)
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)

        # Ensures the mapping exists before we attempt to remove it
        self.assertIn('.txt', organizer.session_extension_map)

        # Simulating user's input to remove mapping
        user_responses = [
            'y', # Response for "Review or modify...?"
            '.txt', # Response for "Enter extension to modify..."
            'ignore', # Response for "New folder..."
            'done' # Response for "Enter extension to modify..."
        ]
        mock_input.side_effect = user_responses

        # Directly calling the edit method
        with self.assertLogs(self.logger, level='INFO') as log_context:
            organizer._interactive_edit_existing_mappings()
        
        # Assertions
        # 1. The organizer's internal state reflects the removal.
        self.assertTrue(organizer._map_changed_this_session, "The change flag should be True after removal.")
        self.assertNotIn('.txt', organizer.session_extension_map, "The key '.txt' should have been removed from the map.")

        # 2. The script confirmed the removal for the user.
        log_output = "\n".join(log_context.output)
        self.assertIn("Mapping for '.txt' removed for this session.", log_output)

        # 3. Interaction with 'input' happened as expected.
        self.assertEqual(mock_input.call_count, 4)

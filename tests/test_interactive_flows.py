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

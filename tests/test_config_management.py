import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import json
from pathlib import Path

from .base_test import BaseOrganizerTest
from organizer import FileOrganizer, DEFAULT_EXTENSION_MAP, APP_NAME, APP_AUTHOR, CONFIG_FILE_NAME

class TestConfigManagement(BaseOrganizerTest):
    """ 
    Tests for configuration management functionalities in FileOrganizer, 
    including loading and saving the extension map.
    """

    def setUp(self):
        """ 
        Extend base setup if needed, or just call super.
        For these tests, we'll primarily be mocking platformdirs and file operations.
        The source/dest dir mocks from BaseOrganizerTest are available but less critical here.
        """
        super().setUp()
    
    # --- Tests for _get_config_file_path ---
    @patch('organizer.Path')
    @patch('organizer.user_config_dir')
    def test_get_config_file_path_creates_dir_and_returns_correct_path(self, mock_user_config_dir_injected: MagicMock, MockPathConstructor_injected: MagicMock):    
        # Set up mock for user_config_dir
        # We will use a subdirectory of the unittest temp directory if we had one
        # Since we are using mocks for Path, we can just set a mocked path
        mock_platform_returned_path_str = "/fake/user/appconfig/File Organizer - CLI Version" 
        mock_user_config_dir_injected.return_value = mock_platform_returned_path_str

        # Creates a mock for Path(mock_platform_config_path_str) that will be returned
        mock_path_instance_for_config_dir = MagicMock(spec=Path)
        
        # It configures the side_effect of the MockPathConstructor to return the correct mock
        # when called with the expected path.
        def path_constructor_side_effect(arg):
            if str(arg) == mock_platform_returned_path_str:
                return mock_path_instance_for_config_dir
            # For other calls to Path, return a new MagicMock or a real Path if necessary
            # so as not to interfere with other parts of the code that might use Path().
            # In this test, we are focused only on this specific call.
            return MagicMock(spec=Path, name=f"GenericPathMock_{str(arg).replace('/', '_')}") 

        MockPathConstructor_injected.side_effect = path_constructor_side_effect

        # It configures what mock_path_instance_for_config_dir / CONFIG_FILE_NAME returns
        mock_final_config_file = MagicMock(spec=Path, name="FinalConfigPath")
        mock_path_instance_for_config_dir.__truediv__.return_value = mock_final_config_file
        mock_final_config_file.__str__.return_value = f"{mock_platform_returned_path_str}/{CONFIG_FILE_NAME}"

        # Mock _load_extension_map_config to avoid problems when starting FileOrganizer
        # which are not the focus of this test.
        with patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
            # Inside this patch, any call to Path(str(mock_resolved_config_dir)) will return mock_resolved_config_dir
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)

        mock_user_config_dir_injected.assert_called_once_with(APP_NAME, APP_AUTHOR, roaming=True)
        MockPathConstructor_injected.assert_any_call(mock_platform_returned_path_str)
        mock_path_instance_for_config_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_path_instance_for_config_dir.__truediv__.assert_called_once_with(CONFIG_FILE_NAME)
        self.assertEqual(organizer.config_path, mock_final_config_file)


    # --- Tests for _load_extension_map_config ---
    @patch('organizer.user_config_dir') # Mock to control config_path
    def test_load_config_no_file_exists_uses_defaults(self, mock_user_config_dir: MagicMock):
        # Simulates that config_path doesn't exist
        mock_config_path_obj = MagicMock(spec=Path)
        mock_config_path_obj.exists.return_value = False

        # Mocks _get_config_file_path to return the mock_config_path_obj
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path_obj):
            with self.assertLogs(self.logger, level='INFO') as log_context:
                organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
        
        self.assertEqual(organizer.session_extension_map, DEFAULT_EXTENSION_MAP)
        self.assertIn("No custom configuration file found. Using default extension map.", "\n".join(log_context.output))
    

    @patch('organizer.user_config_dir')
    def test_load_config_valid_file_merges_with_defaults(self, mock_user_config_dir: MagicMock):
        mock_config_path_obj = MagicMock(spec=Path)
        mock_config_path_obj.exists.return_value = True
        mock_config_path_obj.is_file.return_value = True
        mock_config_path_obj.__str__.return_value = "/fake/config/extension_map_config.json" 

        custom_user_map = {".xyz": "CustomXYZ", ".pdf": "UserPDFDocs"} # .pdf overrides the default

        # Use mock_open to simulate file opening
        # The 'with ... .open() as f' in the original code will be intercepted  
        m_open = mock_open(read_data=json.dumps(custom_user_map)) 

        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path_obj):
            with patch.object(mock_config_path_obj, 'open', m_open): #It mocks the Path obj 'open method'
                with self.assertLogs(self.logger, level='INFO') as log_context:
                    organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
        
        m_open.assert_called_once_with('r', encoding='utf-8')

        expected_map = DEFAULT_EXTENSION_MAP.copy()
        expected_map.update(custom_user_map)
        self.assertEqual(organizer.session_extension_map, expected_map)
        self.assertIn(f"Loaded custom extension map from {mock_config_path_obj}", "\n".join(log_context.output))
    

    @patch('organizer.user_config_dir')
    #@patch('organizer.json.load', side_effect=json.JSONDecodeError("Simulated error", "doc", 0))
    def test_load_config_json_decode_error_uses_defaults(self, mock_user_config_dir: MagicMock):
        mock_config_path_obj = MagicMock(spec=Path)
        mock_config_path_obj.exists.return_value = True
        mock_config_path_obj.is_file.return_value = True
        mock_config_path_obj.__str__.return_value = "/fake/config/corrupted.json"

        m_open = mock_open(read_data="this is not valid json {")
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path_obj):
            with patch.object(mock_config_path_obj, 'open', m_open):
                with self.assertLogs(self.logger, level='WARNING') as log_context:
                    organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
        
        self.assertEqual(organizer.session_extension_map, DEFAULT_EXTENSION_MAP)
        self.assertIn(f"Error decoding JSON from {mock_config_path_obj}", "\n".join(log_context.output))
        self.assertIn("Using default extension map.", "\n".join(log_context.output))
    

    @patch('organizer.user_config_dir')
    def test_load_config_not_a_dictionary_uses_default(self, mock_user_config_dir: MagicMock):
        mock_config_path_obj = MagicMock(spec=Path)
        mock_config_path_obj.exists.return_value = True
        mock_config_path_obj.is_file.return_value = True
        mock_config_path_obj.__str__.return_value = "/fake/config/not_dict.json"

        # Valid JSON, but not a dictionary
        m_open = mock_open(read_data=json.dumps(["this is a list, not a dict"]))
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path_obj):
            with patch.object(mock_config_path_obj, 'open', m_open):
                with self.assertLogs(self.logger, level='WARNING') as log_context:
                    organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
        
        self.assertEqual(organizer.session_extension_map, DEFAULT_EXTENSION_MAP)
        self.assertIn(f"Configuration file {mock_config_path_obj} is not a valid JSON dictionary.", "\n".join(log_context.output))
        self.assertIn("Using default extension map.", "\n".join(log_context.output))
    

    # --- Tests for _save_extension_map_config ---
    @patch('organizer.user_config_dir')
    @patch('builtins.input', return_value='y') # It simulates user typing 'y'
    @patch('organizer.json.dump')
    def test_save_config_changes_made_user_confirms(self, mock_json_dump: MagicMock, mock_input: MagicMock, mock_user_config_dir: MagicMock):
        mock_config_path_obj = MagicMock(spec=Path)
        mock_config_path_obj.__str__.return_value = "/fake/config/save_here.json"

        # It mocks _load_extension_map_config to prevent it from failing due to lack of read_data on open
        # during FileOrganizer initialization in this specific test.
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path_obj):
            with patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
                organizer = FileOrganizer(self.mock_source_dir,self.mock_dest_dir, dry_run=False)
        
        organizer._map_changed_this_session = True # It simulates there were changes
        organizer.session_extension_map = {".test": "TestFolder"} # Map to be saved

        m_open = mock_open()
        # It patches mock_config_path_obj's open method to use mock_open
        with patch.object(mock_config_path_obj, 'open', m_open):
            with self.assertLogs(self.logger, level='INFO') as log_context:
                organizer._save_extension_map_config()
        
        mock_input.assert_called_once_with("Save current extension mappings for future use? (yes/No): ")
        m_open.assert_called_once_with('w', encoding='utf-8')
        mock_json_dump.assert_called_once_with(organizer.session_extension_map, m_open.return_value, indent=4, sort_keys=True)
        self.assertIn(f"Extension mappings saved to {mock_config_path_obj}", "\n".join(log_context.output))
    

    @patch('organizer.user_config_dir')
    @patch('builtins.input', return_value='n') # It simulates the user typing 'n'
    @patch('organizer.json.dump')
    def test_save_config_changes_made_user_declines(self, mock_json_dump: MagicMock, mock_input: MagicMock, mock_user_config_dir: MagicMock):
        mock_config_path_obj = MagicMock(spec=Path)
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path_obj):
            with patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):    
                organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        
        organizer._map_changed_this_session = True

        with self.assertLogs(self.logger, level='INFO') as log_context:
            organizer._save_extension_map_config()
        
        mock_input.assert_called_once_with("Save current extension mappings for future use? (yes/No): ")
        mock_json_dump.assert_not_called()
        self.assertIn("Extension mappings not saved for this session.", "\n".join(log_context.output))


    @patch('organizer.user_config_dir')
    @patch('organizer.json.dump')
    def test_save_config_no_changes_made_logs_appropriately(self, mock_json_dump: MagicMock, mock_user_config_dir: MagicMock):
        mock_config_path_obj = MagicMock(spec=Path)
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path_obj):
            with patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
                organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        
        organizer._map_changed_this_session = False # No changes

        with self.assertLogs(self.logger, level='INFO') as log_context:
            organizer._save_extension_map_config()
        
        mock_json_dump.assert_not_called()
        self.assertIn("No changes made to extension mappings this session. Nothing to save.", "\n".join(log_context.output))
    

    @patch('organizer.user_config_dir')
    @patch('organizer.json.dump')
    def test_save_config_dry_run_logs_appropriately(self, mock_json_dump: MagicMock, mock_user_config_dir: MagicMock):
        """
        Tests that in dry_run mode, if changes WERE made, the save is skipped and logged.
        """
        mock_config_path_obj = MagicMock(spec=Path)
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path_obj), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=True)
        
        organizer._map_changed_this_session = True # It simulates there were changes in the map

        with self.assertLogs(self.logger, level='INFO') as log_context:
            organizer._save_extension_map_config()
        
        # Checks if the file was NOT saved and if the correct log was shown
        mock_json_dump.assert_not_called()
        self.assertIn("Dry run: Configuration changes will not be saved.", "\n".join(log_context.output))
    

    @patch('organizer.user_config_dir')
    @patch('organizer.json.dump')
    def test_save_config_in_dry_run_without_changes_logs_correctly(
        self,
        mock_json_dump: MagicMock,
        mock_user_config_dir: MagicMock
    ):
        """ 
        Tests that even in dry_run mode, if NO changes were made, the 'no changes' log
        is shown, which has precedence.
        """
        mock_config_path_obj = MagicMock(spec=Path)

        # __init__ must be mocked for error-free instantiation
        with patch.object(FileOrganizer, '_get_config_file_path', return_value=mock_config_path_obj), \
            patch.object(FileOrganizer, '_load_extension_map_config', return_value=DEFAULT_EXTENSION_MAP.copy()):
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=True)

        organizer._map_changed_this_session = False 

        with self.assertLogs(self.logger, level='INFO') as log_context:
            organizer._save_extension_map_config()
        
        # Checks that the file was NOT saved and that the "no changes" log was issued
        mock_json_dump.assert_not_called()
        self.assertIn("No changes made to extension mappings this session. Nothing to save.", "\n".join(log_context.output))
            

if __name__ == '__main__':
    unittest.main(verbosity=2)

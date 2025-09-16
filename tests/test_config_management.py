import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
from pathlib import Path

from src.file_organizer import config

class TestConfigManagement(unittest.TestCase):
    """ 
    Unit tests for the configuration management functions in `config.py`.
    """
    
    @patch('src.file_organizer.config.Path')
    @patch('src.file_organizer.config.user_config_dir')
    def test_get_config_file_path_constructs_correct_path(self, mock_user_config_dir: MagicMock, MockPath: MagicMock):
        """
        Verifies that `get_config_file_path` correctly calls platform-specific
        directory functions and constructs the expected file path.
        """
        fake_dir_str = "/fake/config/dir"
        mock_user_config_dir.return_value = fake_dir_str

        mock_path_obj = MagicMock(spec=Path)
        MockPath.return_value = mock_path_obj
        mock_path_obj.__truediv__.return_value = "/fake/config/dir/config.json"

        result = config.get_config_file_path()

        mock_user_config_dir.assert_called_once_with(config.APP_NAME, config.APP_AUTHOR, roaming=True)
        MockPath.assert_called_once_with(fake_dir_str)
        mock_path_obj.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        self.assertEqual(result, "/fake/config/dir/config.json")


    @patch('src.file_organizer.config.get_config_file_path')
    def test_load_extension_map_returns_defaults_when_no_file(self, mock_get_path: MagicMock):
        """
        Verifies that `load_extension_map` returns the default map when the
        configuration file does not exist.
        """
        mock_path_obj = MagicMock(spec=Path)
        mock_path_obj.is_file.return_value = False
        mock_get_path.return_value = mock_path_obj

        with self.assertLogs('src.file_organizer.config', level='INFO') as log_context:
            loaded_map = config.load_extension_map()
        
        self.assertEqual(loaded_map, config.DEFAULT_EXTENSION_MAP)
        mock_get_path.assert_called_once()
        self.assertIn("No custom configuration file found", "\n".join(log_context.output))
    

    @patch('src.file_organizer.config.get_config_file_path')
    def test_load_extension_map_merges_with_defaults(self, mock_get_path: MagicMock):
        """
        Verifies that `load_extension_map` correctly loads a user's
        configuration and merges it with the default settings.
        """

        mock_path_obj = MagicMock(spec=Path)
        mock_path_obj.is_file.return_value = True
        mock_get_path.return_value = mock_path_obj

        user_map = {".xyz": "CustomXYZ", ".pdf": "UserPDFs"}
        m_open = mock_open(read_data=json.dumps(user_map))

        with patch.object(mock_path_obj, 'open', m_open):
            with self.assertLogs('src.file_organizer.config', level='INFO') as log_context:
                loaded_map = config.load_extension_map()
        
        expected_map = config.DEFAULT_EXTENSION_MAP.copy()
        expected_map.update(user_map)
        self.assertEqual(loaded_map, expected_map)

        self.assertIn("Loaded custom extension map", "\n".join(log_context.output))
    

    @patch('src.file_organizer.config.get_config_file_path')
    @patch('src.file_organizer.config.json.dump')
    def test_save_extension_map_writes_to_file(self, mock_json_dump: MagicMock, mock_get_path: MagicMock):
        """
        Verifies that `save_extension_map` correctly serializes a dictionary
        and writes it to the appropriate configuration file.
        """
        mock_path_obj = MagicMock(spec=Path)
        mock_get_path.return_value = mock_path_obj
        
        m_open = mock_open()
        mock_path_obj.open.return_value = m_open()

        map_to_save = {'.test': 'TestFolder'}

        config.save_extension_map(map_to_save)

        # Assertions
        mock_get_path.assert_called_once()
        mock_path_obj.open.assert_called_once_with('w', encoding='utf-8')
        mock_json_dump.assert_called_once_with(map_to_save, m_open(), indent=4, sort_keys=True)

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.file_organizer import cli, config
from .base_test import BaseOrganizerTest

class TestInteractiveFlows(BaseOrganizerTest):
    """
    Tests the interactive user flows handled by the `cli` module, ensuring
    correct orchestration between user input, configuration, and core logic.
    """

    def setUp(self):
        """
        Sets up a consistent state before each test, inheriting file/directory
        mocks and defining a baseline extension map for testing.
        """
        super().setUp()
        self.initial_map = {'.pdf': 'Documents', '.txt': 'TextFiles'}

    
    # --- Editing tests for the 'handle_interactive_edit' function ---
    @patch('builtins.input')
    def test_handle_interactive_edit_changes_mapping(self, mock_input: MagicMock):
        """
        Tests that `handle_interactive_edit` correctly modifies an existing
        mapping in the provided dictionary based on user input.
        """
        session_map = self.initial_map.copy()
        new_folder_name = 'PDF_Files'
        mock_input.side_effect = ['y', '.pdf', new_folder_name, 'done']

        map_was_changed = cli.handle_interactive_edit(session_map)

        self.assertTrue(map_was_changed)
        self.assertEqual(session_map['.pdf'], new_folder_name)
        self.assertEqual(mock_input.call_count, 4)    


    @patch('builtins.input')
    def test_handle_interactive_edit_removes_mapping(self, mock_input: MagicMock):
        """
        Tests that `handle_interactive_edit` correctly removes a mapping
        when the user provides the 'ignore' keyword.
        """
        session_map = self.initial_map.copy()
        mock_input.side_effect = ['y', '.txt', 'ignore', 'done']

        map_was_changed = cli.handle_interactive_edit(session_map)

        self.assertTrue(map_was_changed)
        self.assertNotIn('.txt', session_map)

    
    # --- Integration tests for the 'main' function ---
    @patch('src.file_organizer.config.save_extension_map')
    @patch('src.file_organizer.cli.FileOrganizer')
    @patch('src.file_organizer.config.load_extension_map')
    @patch('builtins.input')
    @patch('sys.argv', ['organizer.py', '/fake/source', '/fake/destination'])
    @patch('pathlib.Path.rglob')
    def test_main_flow_maps_new_extension_and_saves(
        self,
        mock_rglob: MagicMock,
        mock_input: MagicMock,
        mock_load_map: MagicMock,
        MockFileOrganizer: MagicMock,
        mock_save_map: MagicMock
    ):
        """
        Tests the main application flow where a new extension is discovered,
        mapped by the user, and the changes are saved.
        """
        mock_load_map.return_value = self.initial_map.copy()
        mock_rglob.return_value = [self.file_unmapped_ext]
        mock_input.side_effect = ['n', 'CustomData', 'y']
        mock_organizer_instance = MockFileOrganizer.return_value

        cli.main()

        mock_load_map.assert_called_once() # Checks if initial setup loads
        MockFileOrganizer.assert_called_once_with(Path('/fake/source'), Path('/fake/destination')) # Checks if it created the correct directory
        final_map = self.initial_map.copy()
        final_map['.dat'] = 'CustomData'
        mock_organizer_instance.organize.assert_called_once_with(final_map, False) # Checking if map was updated
        mock_save_map.assert_called_once_with(final_map) # Checking if the settings were saved
    
    
    @patch('src.file_organizer.config.save_extension_map')
    @patch('src.file_organizer.cli.FileOrganizer')
    @patch('src.file_organizer.config.load_extension_map')
    @patch('builtins.input')
    @patch('sys.argv', ['organizer.py', '/fake/source', '/fake/destination'])
    @patch('pathlib.Path.rglob')
    def test_main_flow_ignores_new_extension_and_does_not_save(
        self,
        mock_rglob: MagicMock,
        mock_input: MagicMock,
        mock_load_map: MagicMock,
        MockFileOrganizer: MagicMock,
        mock_save_map: MagicMock
    ):
        """
        Tests the main application flow where a new extension is ignored,
        and consequently, no changes are saved.
        """
        mock_load_map.return_value = self.initial_map.copy()
        mock_rglob.return_value = [self.file_unmapped_ext]
        mock_input.side_effect = ['n', '']
        mock_organizer_instance = MockFileOrganizer.return_value

        cli.main()

        mock_organizer_instance.organize.assert_called_once_with(self.initial_map, False) # Checks if original map was called
        mock_save_map.assert_not_called() # Checks if doesn't save the settings
    
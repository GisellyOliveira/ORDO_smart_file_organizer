import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.file_organizer import cli, config
from .base_test import BaseOrganizerTest

class TestCli(BaseOrganizerTest):
    """
    Tests the command-line interface module (`cli.py`).

    This suite includes high-level integration tests for the `main` function,
    verifying argument parsing, component orchestration, and user-interactive
    flows. It also includes unit tests for individual helper functions
    within the cli module.
    """

    def setUp(self):
        """Initializes a baseline extension map for use in tests."""
        super().setUp()
        self.initial_map = {'.pdf': 'Documents', '.txt': 'TextFiles'}

    
    # --- Unit Tests for CLI Helper Functions ---
        
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

    
    # --- Integration Tests for the main() Function ---
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
        Tests the end-to-end application flow where a new extension is
        discovered, mapped by the user, and the changes are saved.
        """
        mock_load_map.return_value = self.initial_map.copy()
        mock_rglob.return_value = [self.file_unmapped_ext]
        mock_input.side_effect = ['n', 'CustomData', 'y']
        mock_organizer_instance = MockFileOrganizer.return_value

        cli.main()

        mock_load_map.assert_called_once() 
        MockFileOrganizer.assert_called_once_with(Path('/fake/source'), Path('/fake/destination')) 
        final_map = self.initial_map.copy()
        final_map['.dat'] = 'CustomData'
        mock_organizer_instance.organize.assert_called_once_with(final_map, False) 
        mock_save_map.assert_called_once_with(final_map) 
    
    
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
        Tests the end-to-end application flow where a new extension is
        ignored by the user, and consequently, no changes are saved.
        """
        mock_load_map.return_value = self.initial_map.copy()
        mock_rglob.return_value = [self.file_unmapped_ext]
        mock_input.side_effect = ['n', '']
        mock_organizer_instance = MockFileOrganizer.return_value

        cli.main()

        mock_organizer_instance.organize.assert_called_once_with(self.initial_map, False) 
        mock_save_map.assert_not_called() 
import unittest
from unittest.mock import patch, MagicMock, call
from pathlib import Path

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

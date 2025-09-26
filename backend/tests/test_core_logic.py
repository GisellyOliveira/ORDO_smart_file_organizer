import unittest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import shutil

from .base_test import BaseOrganizerTest
from src.file_organizer.core import FileOrganizer

class TestCoreLogicAndInitialization(BaseOrganizerTest):
    """
    Tests for the core file organization logic of FileOrganizer.
    """

    def setUp(self):
        """
        Call super().setUp() to get all the common mocks from BaseOrganizerTest.
        """
        super().setUp()
        # The extension map is just a test data
        self.test_extension_map = {'.pdf': 'Documents', '.txt': 'TextFiles', '.png': 'Images'}
    

    # --- Startup Tests ---
    def test_initialization_success(self):
        """Tests successful initialization of the core FileOrganizer."""
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)

        self.assertEqual(organizer.source_dir, self.mock_source_dir)
        self.assertEqual(organizer.dest_dir, self.mock_dest_dir)
        self.assertEqual(organizer.files_moved, 0)
        self.assertEqual(organizer.files_skipped, 0)
    

    def test_init_invalid_source_dir_raises_valueerror(self):
        """Tests that initialization fails with an invalid source directory."""
        self.mock_source_dir.is_dir.return_value = False
        with self.assertRaisesRegex(ValueError, "Source directory does not exist"):
            FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
    

    def test_init_dest_is_file_raises_valueerror(self):
        """Tests that initialization fails if the destination is a file."""
        self.mock_dest_dir.exists.return_value = True
        self.mock_dest_dir.is_dir.return_value = False
        with self.assertRaisesRegex(ValueError, "Destination path exists but is not a directory"):
            FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
    

    # --- Tests for the Organization Logic ---
    @patch('src.file_organizer.core.shutil.move')
    def test_organize_moves_mapped_file_correctly(self, mock_shutil_move: MagicMock):
        """Tests that a file with a mapped extension is moved to the correct category."""
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
        self.mock_source_dir.rglob.return_value = [self.file_pdf1]

        organizer.organize(self.test_extension_map, dry_run=False)

        expected_dest_folder = self.mock_dest_dir / "Documents"
        expected_dest_path = str(expected_dest_folder / self.file_pdf1.name)

        mock_shutil_move.assert_called_once_with(str(self.file_pdf1), expected_dest_path)
        expected_dest_folder.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        self.assertEqual(organizer.files_moved, 1)
    

    @patch('src.file_organizer.core.shutil.move')
    def test_organize_ignores_unmapped_extension(self, mock_shutil_move: MagicMock):
        """Tests that a file with an unmapped extension is ignored."""
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
        # file_unmapped_ext is not at test_extension_map
        self.mock_source_dir.rglob.return_value = [self.file_unmapped_ext]

        organizer.organize(self.test_extension_map, dry_run=False)

        mock_shutil_move.assert_not_called()
        self.assertEqual(organizer.files_moved, 0)
        self.assertEqual(organizer.files_skipped, 0) #File must not be skipped but just ignored.
    

    @patch('src.file_organizer.core.shutil.move')
    def test_deduplication_skips_identical_file(self, mock_shutil_move: MagicMock):
        """Tests that an identical file (same name and hash) at the destination is skipped."""
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
        self.mock_source_dir.rglob.return_value = [self.file_dup_txt_src]

        # Simulates that the destiny file already exists with the same hash
        dest_folder = self.mock_dest_dir / "TextFiles"
        self._configure_destination_file_mock(
            dest_category_folder_mock=dest_folder,
            file_name=self.file_dup_txt_src.name,
            exists=True,
            content_hash="same_hash_for_txt_dup"
        )

        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            organizer.organize({'.txt': 'TextFiles'}, dry_run=False)
        
        mock_shutil_move.assert_not_called()
        self.assertEqual(organizer.files_moved, 0)
        self.assertEqual(organizer.files_skipped, 1)
    

    @patch('src.file_organizer.core.shutil.move')
    def test_deduplication_renames_conflicting_file(self, mock_shutil_move: MagicMock):
        """Tests that a file with the same name but different content is renamed and moved."""
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
        self.mock_source_dir.rglob.return_value = [self.file_dup_img_src]

        # Simulates that the destiny file already exists with a different hash
        dest_folder = self.mock_dest_dir / "Images"
        self._configure_destination_file_mock(
            dest_category_folder_mock=dest_folder,
            file_name=self.file_dup_img_src.name,
            exists=True,
            content_hash="DIFFERENT_HASH"
        )

        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            organizer.organize({'.png': 'Images'}, dry_run=False)
        
        source_file_path_obj = Path(self.file_dup_img_src.name)
        renamed_file_name = f"{source_file_path_obj.stem}(1){source_file_path_obj.suffix}"
        expected_dest_path = str(dest_folder / renamed_file_name)

        mock_shutil_move.assert_called_once_with(str(self.file_dup_img_src), expected_dest_path)
        self.assertEqual(organizer.files_moved, 1)
        self.assertEqual(organizer.files_skipped, 0)
    

    @patch('src.file_organizer.core.shutil.move')
    def test_dry_run_simulates_move_and_rename(self, mock_shutil_move: MagicMock):
        """Tests that dry_run mode logs actions but does not move files."""
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
        # Scenario with a new file (PDF) and a conflicting one (PNG)
        self.mock_source_dir.rglob.return_value = [self.file_pdf1, self.file_dup_img_src]

        dest_folder_png = self.mock_dest_dir / "Images"
        self._configure_destination_file_mock(
            dest_category_folder_mock=dest_folder_png,
            file_name=self.file_dup_img_src.name,
            exists=True,
            content_hash="DIFFERENT_HASH"
        )

        with self.assertLogs('src.file_organizer.core', level='INFO') as log_context:
            with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
                organizer.organize(self.test_extension_map, dry_run=True)
        
        mock_shutil_move.assert_not_called()
        self.assertEqual(organizer.files_moved, 2) # Both should be counted as processed 
        self.assertEqual(organizer.files_skipped, 0)

        log_output = "\n".join(log_context.output)
        self.assertIn(f"[DRY RUN] File '{self.file_pdf1.name}' would be moved to", log_output)
        self.assertIn(f"[DRY RUN] File '{self.file_dup_img_src.name}' would be renamed to", log_output)

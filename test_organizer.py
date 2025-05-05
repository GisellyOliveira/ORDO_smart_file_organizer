import unittest
from unittest.mock import patch, MagicMock, call
import logging
import sys
import shutil
from pathlib import Path
import os 
from organizer import FileOrganizer, EXTENSION_MAP, main, logger


# --- Main Test Class ---
class TestFileOrganizer(unittest.TestCase):
    """
    Comprehensive tests for the FileOrganizer class, focusing on logic,
    file operations (mocked), and edge cases.
    """

    def setUp(self) -> None:
        """
        Set up reusable mock objects for source/destination directories
        and simulated files before each test method runs.
        """
        # Mock for source directory
        self.mock_source_dir = MagicMock(spec=Path, name="SourceDirMock")
        self.mock_source_dir.is_dir.return_value = True
        self.mock_source_dir.__str__.return_value = "/fake/source"

        # Mock for base target directory
        self.mock_dest_dir = MagicMock(spec=Path, name="DestDirMock")
        self.mock_dest_dir.exists.return_value = False # Assumes it does not exist by default
        self.mock_dest_dir.is_dir.return_value = True # Assumes it would be a directory
        self.mock_dest_dir.__str__.return_value = "/fake/destination"

        # --- Mocks for simulated files ---
        self.file_pdf = self._create_mock_file("report.pdf", ".pdf")
        self.file_jpg = self._create_mock_file("photo.jpg", ".jpg")
        self.file_txt = self._create_mock_file("notes.txt", ".txt")
        self.file_no_ext = self._create_mock_file("unknown_file", "") # No extension
        self.file_other_ext = self._create_mock_file("archive.zip", ".zip") # Mapped
        self.file_unmapped_ext = self._create_mock_file("data.custom", ".custom") # Not mapped

        # Mock for subdirectory (organizer.py will ignore it for now)
        self.subdir = MagicMock(spec=Path, name="SubDirMock")
        self.subdir.name = "a_subfolder"
        self.subdir.is_file.return_value = False
        self.subdir.is_dir.return_value = True
        self.subdir.__str__.return_value = "/fake/source/a_subfolder"

        # This sets what mock_source_dir.iterdir() will return
        self.mock_source_dir.iterdir.return_value = [
            self.file_pdf, self.file_jpg, self.subdir, self.file_no_ext,
            self.file_txt, self.file_other_ext, self.file_unmapped_ext
        ]

        # --- Mocks for specific destiny folders ---
        # This simulates the result of self.mock_dest_dir / "SubFolderName"
        self.mock_dest_docs = self._create_mock_dest_path("Documents")
        self.mock_dest_images = self._create_mock_dest_path("Images")
        self.mock_dest_text = self._create_mock_dest_path("TextFiles")
        self.mock_dest_noext = self._create_mock_dest_path("NoExtension")
        self.mock_dest_archives = self._create_mock_dest_path("Archives")
        self.mock_dest_others = self._create_mock_dest_path("Others")

        # It configures mock_dest_dir to return the correct mocks when using '/'
        self.mock_dest_dir.__truediv__.side_effect = self._mock_path_division

    
    def _create_mock_file(self, name: str, suffix: str) -> MagicMock:
        """ Helper function to create a mock file Path object. """
        mock_file = MagicMock(spec=Path, name=f"FileMock_{name}")
        mock_file.name = name
        mock_file.suffix = suffix
        mock_file.is_file.return_value = True
        mock_file.is_dir.return_value = False
        mock_file.__str__.return_value = f"/fake/source/{name}"
        # It simulates file_path.name for '/' operator in destination
        mock_file.__truediv__ = lambda self, other: f"{self}/{other}"
        return mock_file
    

    def _create_mock_dest_path(self, subfolder_name: str) -> MagicMock:
        """ Helper function to create a mock destination Path object. """
        mock_path = MagicMock(spec=Path, name=f"DestMock_{subfolder_name}")
        mock_path.__str__.return_value = f"/fake/destination/{subfolder_name}"
        # It simulates dest_folder / file_name
        def _div_side_effect(self_mock, other_name):
            new_mock = MagicMock(spec=Path)
            new_mock.__str__.return_value = f"{mock_path}/{other_name}"
            return new_mock
        mock_path.__truediv__ = _div_side_effect
        return mock_path
    

    def _mock_path_division(self, subfolder: str) -> MagicMock:
        """ It simulates the / operator for teh base destination directory mock. """
        mapping = {
            "Documents": self.mock_dest_docs,
            "Images": self.mock_dest_images,
            "TextFiles": self.mock_dest_text,
            "NoExtension": self.mock_dest_noext,
            "Archives": self.mock_dest_archives,
            "Others": self.mock_dest_others
        }
        return mapping.get(subfolder, self._create_mock_dest_path(subfolder))
    

    # --- Test Methods ---

    def test_init_success(self):
        """ Tests successful initialization of FileOrganizer. """
        try:
            organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
            self.assertEqual(organizer.source_dir, self.mock_source_dir)
            self.assertEqual(organizer.dest_dir, self.mock_dest_dir)
            self.assertFalse(organizer.dry_run)
        except ValueError:
            self.fail("FileOrganizer initialization raised ValueError unexpectedly.")
    
    
    def test_init_invalid_source_dir(self):
        """ Tests initialization with an invalid source directory. """
        self.mock_source_dir.is_dir.return_value = False # Simulates an invalid source
        with self.assertRaisesRegex(ValueError, "Source directory does not exist"):
            FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
    

    def test_init_dest_is_file(self):
        """ Tests initialization with a destination path that exists but is a file."""
        self.mock_dest_dir.exists.return_value = True
        self.mock_dest_dir.is_dir.return_value = False # Simulates dest is a file
        with self.assertRaisesRegex(ValueError, "Destination path exists but is not a directory"):
            FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
    

    # Patch where functions are used inside the 'organizer' module
    @patch('organizer.shutil.move')
    def test_organize_moves_files_correctly(self, mock_shutil_move):
        """ Tests that files are moved to the correct destination folders. """
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        organizer. organize()

        # 1. Check mkdir calls (should be called for each unique destination folder)
        self.mock_dest_docs.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        self.mock_dest_images.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        self.mock_dest_text.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        self.mock_dest_noext.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        self.mock_dest_archives.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        self.mock_dest_others.mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # 2. Check shutil.move calls (should be called for each file)
        self.assertEqual(mock_shutil_move.call_count, 6) # 6 files, 1 dir ignored
        expected_move_calls = [
            call(str(self.file_pdf), str(self.mock_dest_docs / self.file_pdf.name)),
            call(str(self.file_jpg), str(self.mock_dest_images / self.file_jpg.name)),
            call(str(self.file_no_ext), str(self.mock_dest_noext / self.file_no_ext.name)),
            call(str(self.file_txt), str(self.mock_dest_text / self.file_txt.name)),
            call(str(self.file_other_ext), str(self.mock_dest_archives / self.file_other_ext.name)),
            call(str(self.file_unmapped_ext), str(self.mock_dest_others / self.file_unmapped_ext.name)),
        ]
        # Uses assert_has_calls as the order from iterdir might vary
        mock_shutil_move.assert_has_calls(expected_move_calls, any_order=True)
    

    @patch('organizer.shutil.move')
    def test_organize_dry_run_logs_correctly(self, mock_shutil_move):
        """ Tests that dry_run prevents moving and logs intended actions. """

        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=True)

        # Captures logs during the dry run
        with self.assertLogs(logger='organizer', level='INFO') as log_context: # Captures from specific logger
            organizer.organize()
        
        # 1. Checks that move was NOT called
        mock_shutil_move.assert_not_called()

        # 2. Checks log output for "Would move" messages and summary
        log_output_str = "\n".join(log_context.output) # Join list of logs for easier searching
        self.assertIn("[DRY RUN] Would move 'report.pdf' to '/fake/destination/Documents'", log_output_str)
        self.assertIn("[DRY RUN] Would move 'photo.jpg' to '/fake/destination/Images'", log_output_str)
        self.assertIn("[DRY RUN] Would move 'unknown_file' to '/fake/destination/NoExtension'", log_output_str)
        self.assertIn("[DRY RUN] Would move 'notes.txt' to '/fake/destination/TextFiles'", log_output_str)
        self.assertIn("[DRY RUN] Would move 'archive.zip' to '/fake/destination/Archives'", log_output_str)
        self.assertIn("[DRY RUN] Would move 'data.custom' to '/fake/destination/Others'", log_output_str)
        self.assertIn("Dry run finished. Found 6 files. 6 files would be moved.", log_output_str)
    

    def mock_move_with_log_error(file_path, dest_folder):
        # It simulates the logging that would happen inside the real _move_file
        target_logger = logging.getLogger('organizer')
        target_logger.error(f"Simulated Shutil Error moving file '{file_path.name}'")


    @patch.object(FileOrganizer, '_move_file', side_effect=mock_move_with_log_error)
    def test_organize_handles_move_error(self, mock_move_file):
        """ Tests that errors during shutil.move are caught and logged. """

        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)

        # Captures logs, expecting an ERROR level message
        with self.assertLogs(logger='organizer', level='ERROR') as log_context:
            organizer.organize()
        
        # Checks that move was attempted for all files despite the error
        self.assertEqual(mock_move_file.call_count, 6)
        # Checks the specific error message was logged
        self.assertTrue(any("Simulated Shutil Error moving file" in msg for msg in log_context.output),
                "Expected 'Simulated Shutil Error' log message not found")


# --- Entry Point for Test Execution ---
if __name__=='__main__':
    unittest.main(verbosity=2)
    
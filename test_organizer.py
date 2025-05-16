import unittest
from unittest.mock import patch, MagicMock, call
import logging
from pathlib import Path
from typing import Optional
from organizer import FileOrganizer

logger = logging.getLogger('organizer')

class TestFileOrganizer(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_source_dir = MagicMock(spec=Path, name="SourceDirMock")
        self.mock_source_dir.is_dir.return_value = True
        self.mock_source_dir.__str__.return_value = "/fake/source"

        self.mock_dest_dir = MagicMock(spec=Path, name="DestDirMock")
        self.mock_dest_dir.exists.return_value = False
        self.mock_dest_dir.is_dir.return_value = True
        self.mock_dest_dir.__str__.return_value = "/fake/destination"

        self.configured_dest_file_paths = {}

        self.file_pdf1 = self._create_mock_file("report.pdf", ".pdf", path_prefix="source")
        self.file_docx1 = self._create_mock_file("letter.docx", ".docx", path_prefix="source")
        self.file_epub1 = self._create_mock_file("book.epub", ".epub", path_prefix="source/ebooks_folder")
        self.file_xlsx1 = self._create_mock_file("data.xlsx", ".xlsx", path_prefix="source")
        self.file_csv1 = self._create_mock_file("table.csv", ".csv", path_prefix="source/data_files")
        self.file_jpg1 = self._create_mock_file("image.jpg", ".jpeg", path_prefix="source")
        self.file_png1 = self._create_mock_file("logo.png", ".png", path_prefix="source/assets")
        self.file_svg1 = self._create_mock_file("icon.svg", ".svg", path_prefix="source/vector")
        self.file_psd1 = self._create_mock_file("design.psd", ".psd", path_prefix="source/designs")
        self.file_zip1 = self._create_mock_file("files.zip", ".zip", path_prefix="source")
        self.file_exe1 = self._create_mock_file("installer.exe", ".exe", path_prefix="source/installers")
        self.file_mp3_1 = self._create_mock_file("song.mp3", ".mp3", path_prefix="source/audio_files")
        self.file_wav1 = self._create_mock_file("sound.wav", ".wav", path_prefix="source/audio_files")
        self.file_mp4_1 = self._create_mock_file("movie.mp4", ".mp4", path_prefix="source/video_files")
        self.file_log1 = self._create_mock_file("server.log", ".log", path_prefix="source/logs")
        self.file_json1 = self._create_mock_file("settings.json", ".json", path_prefix="source/configs")
        self.file_yaml1 = self._create_mock_file("app.yaml", ".yaml", path_prefix="source/configs")
        self.file_ttf1 = self._create_mock_file("myfont.ttf", ".ttf", path_prefix="source/fonts_folder")
        self.file_no_ext = self._create_mock_file("no_extension_file", "", path_prefix="source")
        self.file_unmapped_ext = self._create_mock_file("backup.dat", ".dat", path_prefix="source")

        self.file_dup_txt_src = self._create_mock_file("readme_dup.txt", ".txt", path_prefix="source", content_hash="same_hash_for_txt_dup")
        self.file_dup_img_src = self._create_mock_file("photo_dup.png", ".png", path_prefix="source", content_hash="image_hash_source_A")

        self.all_source_files_for_setup = [
            self.file_pdf1, self.file_docx1, self.file_epub1, self.file_xlsx1, self.file_csv1,
            self.file_jpg1, self.file_png1, self.file_svg1, self.file_psd1, self.file_zip1,
            self.file_exe1, self.file_mp3_1, self.file_wav1, self.file_mp4_1, self.file_log1,
            self.file_json1, self.file_yaml1, self.file_ttf1,
            self.file_no_ext, self.file_unmapped_ext,
            self.file_dup_txt_src, self.file_dup_img_src,
        ]
        self.mock_source_dir.rglob.return_value = self.all_source_files_for_setup

        self.mock_dest_textfiles = self._create_mock_dest_category_folder("TextFiles")
        self.mock_dest_documents = self._create_mock_dest_category_folder("Documents")
        self.mock_dest_ebooks = self._create_mock_dest_category_folder("Ebooks")
        self.mock_dest_spreadsheets = self._create_mock_dest_category_folder("Spreadsheets")
        self.mock_dest_data = self._create_mock_dest_category_folder("Data")
        self.mock_dest_images = self._create_mock_dest_category_folder("Images")
        self.mock_dest_vectorgraphics = self._create_mock_dest_category_folder("VectorGraphics")
        self.mock_dest_design_files = self._create_mock_dest_category_folder("Design_Files")
        self.mock_dest_archives = self._create_mock_dest_category_folder("Archives")
        self.mock_dest_executables_installers = self._create_mock_dest_category_folder("Executables_Installers")
        self.mock_dest_music = self._create_mock_dest_category_folder("Music")
        self.mock_dest_audio = self._create_mock_dest_category_folder("Audio")
        self.mock_dest_videos = self._create_mock_dest_category_folder("Videos")
        self.mock_dest_logfiles = self._create_mock_dest_category_folder("LogFiles")
        self.mock_dest_configs = self._create_mock_dest_category_folder("Configs")
        self.mock_dest_fonts = self._create_mock_dest_category_folder("Fonts")

        self.mock_dest_dir.__truediv__.side_effect = self._master_destination_category_folder_division

    def tearDown(self) -> None:
        self.configured_dest_file_paths.clear()

    def _mock_calculate_hash_side_effect(self, file_path_obj: Path, hash_algo: str = "sha256", buffer_size: int = 65536) -> Optional[str]:
        # print(f"TEST_DEBUG _mock_calculate_hash_side_effect: Called for Path='{str(file_path_obj)}', Name='{file_path_obj.name}'")
        if hasattr(file_path_obj, 'mocked_content_hash'):
            # print(f"TEST_DEBUG _mock_calculate_hash_side_effect: Found mocked_content_hash='{file_path_obj.mocked_content_hash}' for '{file_path_obj.name}'. Returning it.")
            return file_path_obj.mocked_content_hash
        else:
            fallback_hash = f"hash_for_{Path(str(file_path_obj)).name}"
            # print(f"TEST_DEBUG _mock_calculate_hash_side_effect: No mocked_content_hash for '{file_path_obj.name}'. Returning fallback_hash='{fallback_hash}'.")
            return fallback_hash

    def _create_mock_file(self, name: str, suffix: str, path_prefix: str = "source", content_hash: Optional[str] = "default_hash") -> MagicMock:
        base_path = "/fake"
        full_path_str: str
        if path_prefix and path_prefix != ".":
            processed_path_prefix = path_prefix.strip('/')
            full_path_str = f"{base_path}/{processed_path_prefix}/{name}"
        else:
            full_path_str = f"{base_path}/{name}"

        mock_file = MagicMock(spec=Path, name=f"FileMock_{name.replace('.', '_')}")
        mock_file.name = name
        mock_file.suffix = suffix.lower()
        mock_file.is_file.return_value = True
        mock_file.is_dir.return_value = False
        mock_file.__str__.return_value = full_path_str
        mock_file.exists.return_value = True
        if content_hash == "default_hash":
            mock_file.mocked_content_hash = f"hash_for_{name.replace('.', '_')}"
        else:
            mock_file.mocked_content_hash = content_hash
        return mock_file

    def _create_mock_dest_category_folder(self, subfolder_name: str) -> MagicMock:
        """Cria um mock para uma PASTA de categoria de destino (ex: /fake/destination/Images)."""
        mock_folder_path = MagicMock(spec=Path, name=f"DestFolderMock_{subfolder_name}")
        # O __str__ representa o caminho da pasta de categoria
        mock_folder_path.__str__.return_value = f"{self.mock_dest_dir}/{subfolder_name}"
        mock_folder_path.name = subfolder_name
        mock_folder_path.exists.return_value = False 
        mock_folder_path.is_dir.return_value = True

        # CORREÇÃO DEFINITIVA (ESPERO) PARA O SIDE_EFFECT DE __truediv__
        # A função side_effect para um operador binário como __truediv__
        # recebe apenas o operando da DIREITA.
        # O operando da ESQUERDA é o mock no qual __truediv__ foi chamado.
        # A lambda captura 'mock_folder_path' do escopo externo para usá-lo como o operando esquerdo.
        def truediv_handler_for_this_folder(right_operand):
            # 'mock_folder_path' aqui é o operando esquerdo (a pasta de categoria)
            # 'right_operand' é o nome do arquivo ou objeto Path
            return self._specific_destination_file_division(mock_folder_path, right_operand)

        mock_folder_path.__truediv__.side_effect = truediv_handler_for_this_folder
        
        return mock_folder_path

    def _master_destination_category_folder_division(self, subfolder_name_str: str) -> MagicMock:
        """
        Chamado quando `self.mock_dest_dir / "CategoryFolder"` é executado.
        Retorna o mock da pasta de categoria apropriado.
        """
        mapping = {
            "TextFiles": self.mock_dest_textfiles, "Documents": self.mock_dest_documents,
            "Ebooks": self.mock_dest_ebooks, "Spreadsheets": self.mock_dest_spreadsheets,
            "Data": self.mock_dest_data, "Images": self.mock_dest_images,
            "VectorGraphics": self.mock_dest_vectorgraphics, "Design_Files": self.mock_dest_design_files,
            "Archives": self.mock_dest_archives, "Executables_Installers": self.mock_dest_executables_installers,
            "Music": self.mock_dest_music, "Audio": self.mock_dest_audio,
            "Videos": self.mock_dest_videos, "LogFiles": self.mock_dest_logfiles,
            "Configs": self.mock_dest_configs, "Fonts": self.mock_dest_fonts,
        }
        return mapping.get(subfolder_name_str, self._create_mock_dest_category_folder(subfolder_name_str))

    def _specific_destination_file_division(self, current_dest_category_folder_mock: MagicMock, file_name_or_path_obj: any) -> MagicMock:
        """
        Chamado quando `mock_categoria_pasta / "nome_arquivo.ext"` é executado.
        Verifica self.configured_dest_file_paths ou cria um mock genérico para o ARQUIVO.
        `current_dest_category_folder_mock` é o mock da pasta de categoria (ex: self.mock_dest_images).
        """
        file_name_str = str(file_name_or_path_obj)
        if isinstance(file_name_or_path_obj, MagicMock) and hasattr(file_name_or_path_obj, 'name'):
            file_name_str = file_name_or_path_obj.name

        full_file_path_key = f"{str(current_dest_category_folder_mock)}/{file_name_str}"

        if full_file_path_key in self.configured_dest_file_paths:
            # print(f"TEST_DEBUG _specific_destination_file_division: Found pre-configured mock for {full_file_path_key}")
            return self.configured_dest_file_paths[full_file_path_key]

        # print(f"TEST_DEBUG _specific_destination_file_division: Creating generic mock for {full_file_path_key}")
        generic_file_mock = MagicMock(spec=Path, name=f"DestFileMock_Generic_{file_name_str.replace('.', '_')}")
        generic_file_mock.__str__.return_value = full_file_path_key
        generic_file_mock.name = file_name_str
        generic_file_mock.stem = Path(file_name_str).stem
        generic_file_mock.suffix = Path(file_name_str).suffix
        generic_file_mock.exists.return_value = False
        return generic_file_mock

    def _configure_destination_file_mock(self, dest_category_folder_mock: MagicMock, file_name: str, exists: bool, content_hash: Optional[str] = "default_hash_for_dest_file") -> MagicMock:
        """
        Helper para criar, configurar e registrar um mock para um arquivo específico no destino.
        Retorna o mock configurado.
        """
        full_path_str = f"{str(dest_category_folder_mock)}/{file_name}"
        
        file_mock = MagicMock(spec=Path, name=f"ConfiguredDestFile_{file_name.replace('.', '_')}")
        file_mock.__str__.return_value = full_path_str
        file_mock.name = file_name
        file_mock.stem = Path(file_name).stem
        file_mock.suffix = Path(file_name).suffix
        file_mock.exists.return_value = exists
        
        if content_hash != "default_hash_for_dest_file":
            file_mock.mocked_content_hash = content_hash
        
        self.configured_dest_file_paths[full_path_str] = file_mock
        return file_mock

    # --- Test Methods ---
    def test_init_success(self):
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
        self.assertEqual(organizer.source_dir, self.mock_source_dir)
        self.assertEqual(organizer.dest_dir, self.mock_dest_dir)
        self.assertFalse(organizer.dry_run)
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)
    
    def test_init_invalid_source_dir(self):
        self.mock_source_dir.is_dir.return_value = False
        with self.assertRaisesRegex(ValueError, "Source directory does not exist or is not a directory"):
            FileOrganizer(self.mock_source_dir, self.mock_dest_dir)
    
    def test_init_dest_is_file(self):
        self.mock_dest_dir.exists.return_value = True
        self.mock_dest_dir.is_dir.return_value = False
        with self.assertRaisesRegex(ValueError, "Destination path exists but is not a directory"):
            FileOrganizer(self.mock_source_dir, self.mock_dest_dir)

    @patch('organizer.shutil.move')
    def test_organize_moves_and_ignores_files(self, mock_shutil_move: MagicMock):
        files_to_process_details = [
            (self.file_pdf1, self.mock_dest_documents), (self.file_docx1, self.mock_dest_documents),
            (self.file_epub1, self.mock_dest_ebooks), (self.file_xlsx1, self.mock_dest_spreadsheets),
            (self.file_csv1, self.mock_dest_data), (self.file_jpg1, self.mock_dest_images),
            (self.file_png1, self.mock_dest_images), (self.file_svg1, self.mock_dest_vectorgraphics),
            (self.file_psd1, self.mock_dest_design_files), (self.file_zip1, self.mock_dest_archives),
            (self.file_exe1, self.mock_dest_executables_installers),
            (self.file_mp3_1, self.mock_dest_music), (self.file_wav1, self.mock_dest_audio),
            (self.file_mp4_1, self.mock_dest_videos), (self.file_log1, self.mock_dest_logfiles),
            (self.file_json1, self.mock_dest_data), (self.file_yaml1, self.mock_dest_configs),
            (self.file_ttf1, self.mock_dest_fonts),
            (self.file_dup_txt_src, self.mock_dest_textfiles),
            (self.file_dup_img_src, self.mock_dest_images),
        ]
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            organizer.organize()

        expected_mkdir_target_folders = {details[1] for details in files_to_process_details}
        for folder_mock in expected_mkdir_target_folders:
            folder_mock.mkdir.assert_any_call(parents=True, exist_ok=True)
        
        self.assertEqual(mock_shutil_move.call_count, len(files_to_process_details))
        expected_move_calls = [
            call(str(file_mock), f"{str(dest_folder_mock)}/{file_mock.name}")
            for file_mock, dest_folder_mock in files_to_process_details
        ]
        mock_shutil_move.assert_has_calls(expected_move_calls, any_order=True)
        self.assertEqual(organizer.files_successfully_moved_or_renamed, len(files_to_process_details))
        self.assertEqual(organizer.skipped_identical_duplicates, 0)

    @patch('organizer.shutil.move')
    def test_organize_dry_run_logs_correctly(self, mock_shutil_move: MagicMock):
        self._configure_destination_file_mock(
            dest_category_folder_mock=self.mock_dest_textfiles, 
            file_name=self.file_dup_txt_src.name, 
            exists=True, 
            content_hash="hash_para_readme_dup_no_destino_dry_run" 
        )

        files_expected_to_be_logged_as_considered = [
            (self.file_pdf1, self.mock_dest_documents), (self.file_docx1, self.mock_dest_documents),
            (self.file_epub1, self.mock_dest_ebooks), (self.file_xlsx1, self.mock_dest_spreadsheets),
            (self.file_csv1, self.mock_dest_data), (self.file_jpg1, self.mock_dest_images),
            (self.file_png1, self.mock_dest_images), (self.file_svg1, self.mock_dest_vectorgraphics),
            (self.file_psd1, self.mock_dest_design_files), (self.file_zip1, self.mock_dest_archives),
            (self.file_exe1, self.mock_dest_executables_installers),
            (self.file_mp3_1, self.mock_dest_music), (self.file_wav1, self.mock_dest_audio),
            (self.file_mp4_1, self.mock_dest_videos), (self.file_log1, self.mock_dest_logfiles),
            (self.file_json1, self.mock_dest_data), (self.file_yaml1, self.mock_dest_configs),
            (self.file_ttf1, self.mock_dest_fonts),
            (self.file_dup_txt_src, self.mock_dest_textfiles), 
            (self.file_dup_img_src, self.mock_dest_images),
        ]
        files_to_be_ignored_by_rule = [self.file_no_ext, self.file_unmapped_ext]
        
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=True)
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            with self.assertLogs(logger='organizer', level='DEBUG') as log_context_debug:
                organizer.organize()
        
        mock_shutil_move.assert_not_called()
        log_output_str = "\n".join(log_context_debug.output)

        for file_mock, dest_folder_mock in files_expected_to_be_logged_as_considered:
            expected_dest_path_str = f"{str(dest_folder_mock)}/{file_mock.name}"
            if expected_dest_path_str in self.configured_dest_file_paths and \
               self.configured_dest_file_paths[expected_dest_path_str].exists.return_value:
                 self.assertIn(f"[DRY RUN] File '{file_mock.name}' already exists at '{str(dest_folder_mock)}'.", log_output_str)
            else:
                self.assertIn(f"[DRY RUN] Would move '{file_mock.name}' to '{expected_dest_path_str}'", log_output_str)

        self.assertIn(f"Ignoring file '{self.file_no_ext.name}' (reason: no extension)", log_output_str)
        self.assertIn(f"Ignoring file '{self.file_unmapped_ext.name}' (reason: extension '{self.file_unmapped_ext.suffix}' not in EXTENSION_MAP)", log_output_str)
        
        total_scanned = len(self.all_source_files_for_setup)
        num_ignored = len(files_to_be_ignored_by_rule)
        num_considered = len(files_expected_to_be_logged_as_considered)
        self.assertIn(f"Total files scanned: {total_scanned}", log_output_str)
        self.assertIn(f"Files ignored by extension rules: {num_ignored}", log_output_str)
        self.assertIn(f"Files that would be considered for moving/renaming (passed extension filter): {num_considered}", log_output_str)

    @patch('organizer.shutil.move')
    def test_organize_deduplication_skips_identical_file(self, mock_shutil_move: MagicMock):
        self.mock_source_dir.rglob.return_value = [self.file_dup_txt_src]
        
        self._configure_destination_file_mock(
            dest_category_folder_mock=self.mock_dest_textfiles,
            file_name=self.file_dup_txt_src.name,
            exists=True,
            content_hash="same_hash_for_txt_dup"
        )

        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            with self.assertLogs(logger='organizer', level='INFO') as log_context:
                organizer.organize()

        mock_shutil_move.assert_not_called()
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 1)
        log_output_str = "\n".join(log_context.output)
        self.assertIn(f"Skipping identical file (same name '{self.file_dup_txt_src.name}', same hash)", log_output_str)

    @patch('organizer.shutil.move')
    def test_organize_deduplication_renames_conflicting_file(self, mock_shutil_move:MagicMock):
        self.mock_source_dir.rglob.return_value = [self.file_dup_img_src]

        self._configure_destination_file_mock(
            dest_category_folder_mock=self.mock_dest_images,
            file_name=self.file_dup_img_src.name,
            exists=True,
            content_hash="image_hash_dest_B_different"
        )
        
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            with self.assertLogs(logger='organizer', level='INFO') as log_context:
                organizer.organize()

        base_name_stem = Path(self.file_dup_img_src.name).stem
        base_name_suffix = Path(self.file_dup_img_src.name).suffix
        renamed_file_name = f"{base_name_stem}(1){base_name_suffix}"
        expected_renamed_path_str = f"{self.mock_dest_images}/{renamed_file_name}"
        
        mock_shutil_move.assert_called_with(str(self.file_dup_img_src), expected_renamed_path_str)
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 1)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)
        log_output_str = "\n".join(log_context.output)
        self.assertIn(f"File '{self.file_dup_img_src.name}' exists at '{str(self.mock_dest_images)}' but with different content", log_output_str)
        self.assertIn(f"Moving (renamed) '{self.file_dup_img_src.name}' to '{expected_renamed_path_str}'", log_output_str)

    @patch('organizer.shutil.move', side_effect=Exception("Simulated Shutil Error during actual move operation"))
    def test_organize_handles_shutil_move_error(self, mock_shutil_move_with_error: MagicMock):
        self.mock_source_dir.rglob.return_value = [self.file_pdf1]
        
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect):
            with self.assertLogs(logger='organizer', level='ERROR') as log_context:
                organizer.organize()

        expected_dest_path_str = f"{self.mock_dest_documents}/{self.file_pdf1.name}"
        mock_shutil_move_with_error.assert_called_once_with(str(self.file_pdf1), expected_dest_path_str)
        log_output_str = "\n".join(log_context.output)
        self.assertIn(f"Unexpected error moving file '{self.file_pdf1.name}' to '{expected_dest_path_str}'", log_output_str)
        self.assertIn("Simulated Shutil Error during actual move operation", log_output_str)
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)
        self.assertEqual(organizer.skipped_identical_duplicates, 0)

    @patch('organizer.shutil.move')
    def test_organize_skips_file_on_source_hash_calculation_error(self, mock_shutil_move: MagicMock):
        self.mock_source_dir.rglob.return_value = [self.file_pdf1]
        self.file_pdf1.mocked_content_hash = None 

        self._configure_destination_file_mock(
            dest_category_folder_mock=self.mock_dest_documents,
            file_name=self.file_pdf1.name,
            exists=True,
            content_hash="dummy_dest_hash_when_source_fails" 
        )
        
        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect) as mock_calc_hash:
            with self.assertLogs(logger='organizer', level='ERROR') as log_context:
                organizer.organize()

        source_call_made = any(call_args[0][0] is self.file_pdf1 for call_args in mock_calc_hash.call_args_list)
        self.assertTrue(source_call_made, "Hash calculation not attempted for source file.")
        mock_shutil_move.assert_not_called()
        self.assertIn(f"Skipping '{self.file_pdf1.name}' due to error calculating its hash.", "\n".join(log_context.output))
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)

    @patch('organizer.shutil.move')
    def test_organize_skips_file_on_destination_hash_calculation_error_when_conflict(self, mock_shutil_move: MagicMock):
        self.mock_source_dir.rglob.return_value = [self.file_pdf1]
        self.file_pdf1.mocked_content_hash = "valid_source_hash_pdf1"

        configured_dest_mock = self._configure_destination_file_mock(
            dest_category_folder_mock=self.mock_dest_documents,
            file_name=self.file_pdf1.name,
            exists=True,
            content_hash=None 
        )

        organizer = FileOrganizer(self.mock_source_dir, self.mock_dest_dir, dry_run=False)
        with patch.object(organizer, '_calculate_file_hash', side_effect=self._mock_calculate_hash_side_effect) as mock_calc_hash:
            with self.assertLogs(logger='organizer', level='ERROR') as log_context:
                organizer.organize()
        
        source_call_made = any(call_args[0][0] is self.file_pdf1 for call_args in mock_calc_hash.call_args_list)
        dest_call_made = any(call_args[0][0] is configured_dest_mock for call_args in mock_calc_hash.call_args_list)

        self.assertTrue(source_call_made, "Hash calc not called for source")
        self.assertTrue(dest_call_made, "Hash calc not called for pre-configured destination conflict file")
        mock_shutil_move.assert_not_called()
        log_output_str = "\n".join(log_context.output)
        self.assertIn(f"Skipping '{self.file_pdf1.name}'. Could not calculate hash for existing destination file '{configured_dest_mock.name}'.", log_output_str)
        self.assertEqual(organizer.files_successfully_moved_or_renamed, 0)

if __name__=='__main__':
    unittest.main(verbosity=2)

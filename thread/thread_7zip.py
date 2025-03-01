# 7zip子线程
import os
import re
import subprocess

from PySide6.QtCore import QThread, Signal

from constant import _PASSWORD_FAKE, _TEMP_FOLDER, _PATH_7ZIP
from module import function_password, function_7zip, function_normal
from module.function_7zip import Result7zip
from module.function_config import GetSetting


class Thread7zip(QThread):
    signal_start = Signal()
    signal_stop = Signal()
    signal_finish = Signal()
    signal_finish_restart = Signal(list)
    signal_current_file = Signal(str)
    signal_schedule_file = Signal(str)
    signal_schedule_test = Signal(str)
    signal_schedule_extract = Signal(int)
    signal_7zip_result = Signal(object)

    def __init__(self):
        super().__init__()
        self._is_stop_thread = False  
        self._file_dict = dict() 
        # 读取密码
        self._passwords = None
        # 读取配置
        self._mode_extract = None
        self._extract_to_folder = None
        self._delete_file = None 
        self._handle_multi_archive = None  
        self._output_folder = None 
        self._filter_suffix = None 
        self._extract_file_result = []

    def set_file_dict(self, file_dict: dict):
        self._file_dict = file_dict

    def stop(self):
        self._is_stop_thread = True

    def _update_setting(self):

        passwords_filename = function_password.read_password_from_files(list(self._file_dict.keys()))
        self._passwords = [_PASSWORD_FAKE] + passwords_filename + function_password.read_password()

        self._mode_extract = GetSetting.mode_extract()
        self._extract_to_folder = GetSetting.extract_to_folder()  
        self._delete_file = GetSetting.delete_file()  
        self._handle_multi_folder = GetSetting.handle_multi_folder() 
        self._handle_multi_archive = GetSetting.handle_multi_archive() 
        self._output_folder = GetSetting.output_folder()  
        self._filter_suffix = ['-xr!*.' + i for i in GetSetting.filter_suffix().split(' ') if i] 

    def run(self):
        pass
        self._is_stop_thread = False
        self._extract_file_result.clear()
        self._update_setting()

        self.signal_start.emit()

        count_file = len(self._file_dict)
        for index, file_first in enumerate(self._file_dict, start=1):
            if not os.path.exists(file_first):
                continue
            if self._is_stop_thread:
                break
            self.signal_current_file.emit(os.path.basename(file_first))
            self.signal_schedule_file.emit(f'{index}/{count_file}')

            fake_test_result, archive_info_dict = function_7zip.test_fake_password(file_first)
            if fake_test_result is True:  
                self._test_file_command_l(file_first, self._passwords)
            elif fake_test_result is False: 
                if self._mode_extract: 
                    self._extract_file(file_first, self._passwords)
                else: 
                    paths_inside = archive_info_dict['paths']
                    if paths_inside:
                        check_path_inside = paths_inside[0]  
                    else:
                        check_path_inside = None
                    self._test_file(file_first, self._passwords, check_path_inside=check_path_inside)
            else: 
                self.signal_7zip_result.emit(fake_test_result)

            if self._mode_extract:
                self._delete_temp_folder(file_first)

        if self._is_stop_thread:
            self.signal_stop.emit()
        else:
            if self._mode_extract and self._handle_multi_archive:
                self.signal_finish_restart.emit(self._extract_file_result)
            else:
                self.signal_finish.emit()

    def _test_file(self, file, passwords, check_path_inside=None):
        count_password = len(passwords)
        result = Result7zip.WrongPassword  
        for index_password, password in enumerate(passwords, start=1):
            if self._is_stop_thread:
                break
            self.signal_schedule_test.emit(f'{index_password}/{count_password}')
            result, _ = function_7zip.call_7zip('t', file, password, check_path_inside=check_path_inside)
            if not isinstance(result, Result7zip.WrongPassword):  
                break

        self.signal_7zip_result.emit(result)

    def _test_file_command_l(self, file, passwords):

        count_password = len(passwords)
        result = Result7zip.WrongPassword 
        right_password = _PASSWORD_FAKE
        for index_password, password in enumerate(passwords, start=1):
            if self._is_stop_thread:
                break
            self.signal_schedule_test.emit(f'{index_password}/{count_password}')
            result, _ = function_7zip.call_7zip('l', file, password)
            if not isinstance(result, Result7zip.WrongPassword):  
                right_password = password
                break

        if isinstance(result, Result7zip.Success) and self._mode_extract: 
            self._extract_file(file, right_password)
        else:
            self.signal_7zip_result.emit(result)

    def _extract_file(self, file, passwords):
        if isinstance(passwords, str):
            passwords = [passwords]

        if self._output_folder:
            temp_folder = os.path.normpath(os.path.join(self._output_folder, _TEMP_FOLDER))
        else:  
            temp_folder = os.path.normpath(os.path.join(os.path.dirname(file), _TEMP_FOLDER))
        filetitle = function_normal.get_filetitle(file)
        extract_folder = os.path.normpath(os.path.join(temp_folder, filetitle))

        count_password = len(passwords)
        result = Result7zip.WrongPassword 

        for index_password, password in enumerate(passwords, start=1):
            if self._is_stop_thread:
                break
            self.signal_schedule_test.emit(f'{index_password}/{count_password}')
            result = self._run_7zip_x(file, extract_folder, password)
            if not isinstance(result, Result7zip.WrongPassword): 
                break

        self.signal_7zip_result.emit(result)

        if isinstance(result, Result7zip.Success):
            if self._delete_file:
                files_list = self._file_dict[file]
                function_normal.delete_files(files_list)


            need_move_path = extract_folder 

            listdir = os.listdir(extract_folder)
            if len(listdir) == 1:
                need_move_path = os.path.normpath(os.path.join(extract_folder, listdir[0]))
            if self._handle_multi_folder:
                need_move_path = function_normal.get_first_multi_path(extract_folder)

            parent_folder = os.path.dirname(temp_folder)
            if self._extract_to_folder:
                
                target_folder = os.path.normpath(os.path.join(parent_folder, filetitle))
                target_folder = os.path.normpath(os.path.join(
                    parent_folder, function_normal.create_nodup_filename(target_folder, parent_folder)))
                if len(listdir) == 1:
                    _path = os.path.normpath(os.path.join(extract_folder, listdir[0]))
                    if os.path.isdir(_path) and os.path.basename(_path) == os.path.basename(target_folder):
                        target_folder = parent_folder
            else:
                target_folder = parent_folder

            final_path = function_normal.move_file(need_move_path, target_folder)
            self._extract_file_result.append(final_path)

        function_normal.delete_empty_folder(extract_folder)

    def _run_7zip_x(self, file, extract_folder, password):
        _7zip_command = [_PATH_7ZIP, 'x', '-y', file,
                         '-bsp1', '-bse1', '-bso1',
                         '-o' + extract_folder,
                         '-p' + password] + self._filter_suffix

        print('测试 7zip命令', _7zip_command)
        process = subprocess.Popen(_7zip_command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   creationflags=subprocess.CREATE_NO_WINDOW,
                                   text=True,
                                   universal_newlines=True)


        result_error = Result7zip.WrongPassword(file) 
        pre_progress = 0 
        is_read_stderr = True  
        is_read_progress = True 

        while True:
            try:
                output = process.stdout.readline()
                print('【7zip解压信息：', output, '】')  
            except UnicodeDecodeError:
                # UnicodeDecodeError: 'gbk' codec can't decode byte 0xaa in position 32: illegal multibyte sequence
                output = ''
            if output == '' and process.poll() is not None:  
                break
            if output and is_read_stderr:  
                is_wrong_password = re.search('Wrong password', output)
                is_missing_volume = re.search('Missing volume', output)
                is_not_archive = re.search('Cannot open the file as', output)
                if is_wrong_password:
                    result_error = Result7zip.WrongPassword(file)
                    is_read_stderr = False
                    is_read_progress = False
                elif is_missing_volume:
                    result_error = Result7zip.MissingVolume(file)
                    is_read_stderr = False
                    is_read_progress = False
                elif is_not_archive:  
                    result_error = Result7zip.NotArchiveOrDamaged(file)

            if output and is_read_progress: 

                match_progress = re.search(r'(\d{1,3})% *\d*', output)
                if match_progress:
                    is_read_stderr = False
                    current_progress = int(match_progress.group(1)) 
                    if current_progress > pre_progress:
                        self.signal_schedule_extract.emit(current_progress)
                        pre_progress = current_progress  

        if process.poll() == 0: 
            if os.path.exists(extract_folder):
                result = Result7zip.Success(file, password)
            else:
                result = Result7zip.UnknownError(file)
        elif process.poll() == 1:  
            result = Result7zip.FileOccupied(file)
        elif process.poll() == 2:  
            result = result_error
        elif process.poll() == 8: 
            result = Result7zip.NotEnoughSpace(file)
        else: 
            result = Result7zip.UnknownError(file)

        return result

    def _delete_temp_folder(self, file):
        if self._output_folder:
            temp_folder = os.path.normpath(os.path.join(self._output_folder, _TEMP_FOLDER))
        else: 
            temp_folder = os.path.normpath(os.path.join(os.path.dirname(file), _TEMP_FOLDER))
        if os.path.exists(temp_folder):
            function_normal.delete_empty_folder(temp_folder)

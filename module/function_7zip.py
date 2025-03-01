# 调用7zip的相关方法

import subprocess

from constant import _PATH_7ZIP, _PASSWORD_FAKE, _COLOR_SKIP, _COLOR_ERROR, _COLOR_WARNING, _COLOR_SUCCESS


def call_7zip(command_type: str, filepath: str, password: str, check_path_inside=None):

    command = [_PATH_7ZIP,
               command_type,
               filepath,
               "-p" + password]
    if command_type == 't' and check_path_inside:  
        command.append(check_path_inside)
    print('测试 7zip命令', command)
    process = subprocess.run(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             creationflags=subprocess.CREATE_NO_WINDOW,
                             text=True,
                             universal_newlines=True)

    if process.returncode == 0: 
        result_class = Result7zip.Success(filepath, password)
    elif process.returncode == 1: 
        result_class = Result7zip.FileOccupied(filepath)
    elif process.returncode == 2:  
        stderr = str(process.stderr) + str(process.stdout)  
        print('【7zip测试信息：', stderr, '】')  
        if 'Wrong password' in stderr:
            result_class = Result7zip.WrongPassword(filepath)
        elif 'Missing volume' in stderr:
            result_class = Result7zip.MissingVolume(filepath)
        elif 'Cannot open the file as' in stderr:  
            result_class = Result7zip.NotArchiveOrDamaged(filepath)
        else: 
            result_class = Result7zip.UnknownError(filepath)
    elif process.returncode == 8: 
        result_class = Result7zip.NotEnoughSpace(filepath)
    else:  
        result_class = Result7zip.UnknownError(filepath)


    archive_info_dict = get_info_from_stdout(process.stdout)

    return result_class, archive_info_dict


def test_fake_password(file):

    result_class, archive_info_dict = call_7zip('l', file, _PASSWORD_FAKE)
    if isinstance(result_class, Result7zip.WrongPassword):
        return True, archive_info_dict
    elif isinstance(result_class, Result7zip.Success):
        return False, archive_info_dict
    else:
        return result_class, archive_info_dict


class Result7zip:

    class _Template:
        def __init__(self, file, text, color):
            self.file = file
            self.text = text
            self.color = color

    class Skip(_Template):

        def __init__(self, file):
            super().__init__(file, '跳过', _COLOR_SKIP)

    class WrongPassword(_Template):

        def __init__(self, file):
            super().__init__(file, '密码错误', _COLOR_ERROR)

    class MissingVolume(_Template):

        def __init__(self, file):
            super().__init__(file, '缺少分卷', _COLOR_ERROR)

    class NotArchiveOrDamaged(_Template):

        def __init__(self, file):
            super().__init__(file, '不是压缩文件或文件已经损坏', _COLOR_ERROR)

    class UnknownError(_Template):

        def __init__(self, file):
            super().__init__(file, '未知错误', _COLOR_ERROR)

    class FileOccupied(_Template):

        def __init__(self, file):
            super().__init__(file, '文件被占用', _COLOR_WARNING)

    class NotEnoughSpace(_Template):

        def __init__(self, file):
            super().__init__(file, '磁盘空间不足', _COLOR_WARNING)

    class Success(_Template):

        def __init__(self, file, password):
            super().__init__(file, '成功', _COLOR_SUCCESS)
            self.password = password if password != _PASSWORD_FAKE else ''


class Collect7zipResult:
    _instance = None
    _is_init = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._is_init:
            super().__init__()
            self._is_init = True

            self._result_dict = dict()  # 结果字典，key为文件路径，value为Result7zip对象

    def reset_count(self):
        self._result_dict.clear()

    def collect(self, result_class):
        file = result_class.file
        self._result_dict[file] = result_class

    def get_result_text(self):
        wrong_password = 0  # 密码错误
        missing_volume = 0  # 缺少分卷
        not_archive_or_damaged = 0  # 不是压缩文件或文件已经损坏
        unknown_error = 0  # 未知错误
        file_occupied = 0  # 文件被占用
        not_enough_space = 0  # 磁盘空间不足
        success = 0  # 成功

        for result_class in self._result_dict.values():
            if isinstance(result_class, Result7zip.WrongPassword):
                wrong_password += 1
            elif isinstance(result_class, Result7zip.MissingVolume):
                missing_volume += 1
            elif isinstance(result_class, Result7zip.NotArchiveOrDamaged):
                not_archive_or_damaged += 1
            elif isinstance(result_class, Result7zip.UnknownError):
                unknown_error += 1
            elif isinstance(result_class, Result7zip.FileOccupied):
                file_occupied += 1
            elif isinstance(result_class, Result7zip.NotEnoughSpace):
                not_enough_space += 1
            elif isinstance(result_class, Result7zip.Success):
                success += 1

        count_success = success
        count_wrong_password = wrong_password
        count_error = missing_volume + not_archive_or_damaged + unknown_error + file_occupied + not_enough_space
        join_text = f'成功:{count_success} 失败:{count_wrong_password} 错误:{count_error}'

        return join_text


def get_info_from_stdout(stdout_text: str):
    data_dict = {'filetype': None, 'paths': None}
    if stdout_text:
        text_split = stdout_text.splitlines()
    else:
        return data_dict

    cut_ = [i for i in text_split if i.startswith('Type = ')]
    if cut_:
        cut_text = [i for i in text_split if i.startswith('Type = ')][0]
        filetype = cut_text[len('Type = '):]
        data_dict['filetype'] = filetype
    start_index = None
    end_index = None
    for index, i in enumerate(text_split):
        if i.startswith('   Date'):
            start_index = index
        if i.startswith('----------'):
            end_index = index
    if start_index or end_index:
        column_name_index = text_split[start_index].find('Name')
        cut_text = text_split[start_index + 2:end_index]
        paths = [i[column_name_index:] for i in cut_text if 'D....' not in i]
        data_dict['paths'] = paths

    return data_dict

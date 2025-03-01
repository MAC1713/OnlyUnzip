# 压缩文件相关方法
import os
import re
from typing import Union

import filetype

from constant import PATTERN_7Z, PATTERN_RAR_WITHOUT_SUFFIX, PATTERN_ZIP, PATTERN_ZIP_VOLUME, PATTERN_ZIP_TYPE2, \
    PATTERN_RAR


def is_archive(filepath: str) -> Union[bool, str]:

    archive_type = ['zip', 'tar', 'rar', 'gz', '7z', 'xz', 'iso']
    if not os.path.exists(filepath):
        return False
    elif os.path.isdir(filepath):
        return False
    else:
        file_suffix = os.path.splitext(filepath)[1][1:].lower() 
        if file_suffix in archive_type:
            print(filepath, ' 文件类型 ', file_suffix)
            return file_suffix

        kind = filetype.guess(filepath)
        if kind is None:
            return False
        else:
            type_kind = kind.extension
            if type_kind in archive_type:
                print(filepath, ' 文件类型 ', type_kind)
                return type_kind

        return False


def split_archive(archives: list) -> dict:
  
    file_dict = {} 
    archives = [os.path.normpath(i) for i in archives]
    archives = list(set(archives))
  
    volume_archives = []  
    for file in archives:
        if is_volume_archive(file):
            volume_archives.append(file)
        else:
            file_dict[file] = set()
            file_dict[file].add(file)


    split_folder_dict = {}  
    for path in volume_archives:
        parent_folder = os.path.dirname(path)
        if parent_folder not in split_folder_dict:
            split_folder_dict[parent_folder] = []
        split_folder_dict[parent_folder].append(path)
   
    dirpath_list = set()
    for dirpath, files in split_folder_dict.items():
       
        dirpath_list.add(dirpath)
        for file in files:
            first_volume_path = create_fake_first_volume_path(file)
            if first_volume_path not in file_dict:
                file_dict[first_volume_path] = set()
            file_dict[first_volume_path].add(file)
    for dirpath in dirpath_list:
        listdir = [os.path.normpath(os.path.join(dirpath, i)) for i in os.listdir(dirpath)]
        for file in listdir:
            if is_volume_archive(file):
                first_volume_path = create_fake_first_volume_path(file)
                if first_volume_path in file_dict:
                    file_dict[first_volume_path].add(file)

    return file_dict


def is_volume_archive(file):
    filename = os.path.basename(file)
    if (re.match(PATTERN_7Z, filename, flags=re.I)
            or re.match(PATTERN_RAR, filename, flags=re.I)
            or re.match(PATTERN_RAR_WITHOUT_SUFFIX, filename, flags=re.I)
            or re.match(PATTERN_ZIP, filename, flags=re.I)
            or re.match(PATTERN_ZIP_VOLUME, filename, flags=re.I)
            or re.match(PATTERN_ZIP_TYPE2, filename, flags=re.I)):
        return True
    else:
        return False


def create_fake_first_volume_path(file, return_filetitle=False):
    dir_, filename = os.path.split(file)
    filetitle = os.path.splitext(filename)[0] 
    if re.match(PATTERN_7Z, filename, flags=re.I):
        filetitle = re.match(PATTERN_7Z, filename, flags=re.I).group(1)
        first_volume_path = os.path.normpath(os.path.join(dir_, filetitle + '.7z.001'))
    elif re.match(PATTERN_RAR, filename, flags=re.I):
        filetitle = re.match(PATTERN_RAR, filename, flags=re.I).group(1)
        number_length = len(re.match(PATTERN_RAR, filename, flags=re.I).group(2))  # 解决part1.rar和part01.rar的情况
        first_volume_path = os.path.normpath(os.path.join(dir_, filetitle + f'.part{"1".zfill(number_length)}.rar'))
    elif re.match(PATTERN_RAR_WITHOUT_SUFFIX, filename, flags=re.I):
        filetitle = re.match(PATTERN_RAR_WITHOUT_SUFFIX, filename, flags=re.I).group(1)
        number_length = len(re.match(PATTERN_RAR_WITHOUT_SUFFIX, filename, flags=re.I).group(2))
        first_volume_path = os.path.normpath(os.path.join(dir_, filetitle + f'.part{"1".zfill(number_length)}'))
    elif re.match(PATTERN_ZIP, filename, flags=re.I):
        first_volume_path = file
    elif re.match(PATTERN_ZIP_VOLUME, filename, flags=re.I):
        filetitle = re.match(PATTERN_ZIP_VOLUME, filename, flags=re.I).group(1)
        first_volume_path = os.path.normpath(os.path.join(dir_, filetitle + '.zip'))
    elif re.match(PATTERN_ZIP_TYPE2, filename, flags=re.I):
        filetitle = re.match(PATTERN_ZIP_TYPE2, filename, flags=re.I).group(1)
        first_volume_path = os.path.normpath(os.path.join(dir_, filetitle + '.zip.001'))
    else:
        return False

    if return_filetitle:
        return filetitle
    else:
        return os.path.normpath(first_volume_path)

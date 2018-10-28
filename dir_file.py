#!/usr/bin/python  
# -*- coding:utf8 -*-  

import os
import re
import config as cf


def dirFilePath(level, path,file_path_list = None):
    # 所有文件夹，第一个字段是次目录的级别
    dirList = []
    # 所有文件  
    fileList = []
    if file_path_list is None:
        file_path_list = []
    # 返回一个列表，其中包含在目录条目的名称(google翻译)  
    files = os.listdir(path)
    # 先添加目录级别
    dirList.append(str(level))
    for f in files:
        if(os.path.isdir(path + '/' + f)):
            # 排除隐藏文件夹。因为隐藏文件夹过多  
            if(f[0] == '.'):
                pass
            else:
                # 添加非隐藏文件夹  
                dirList.append(f)
        if(os.path.isfile(path + '/' + f)):
            # 添加文件
            a =  []
            a.append(path + '/' + f)
            a.append(f)
            file_path_list.append(a)
            fileList.append(f)
            # 当一个标志使用，文件夹列表第一个级别不打印
    i_dl = 0
    for dl in dirList:
        if(i_dl == 0):
            i_dl = i_dl + 1
        else:
            # 打印至控制台，不是第一个的目录  
            # print('-' * (int(dirList[0])), dl)
            # 打印目录下的所有文件夹和文件，目录级别+1  
            file_path_list = dirFilePath((int(dirList[0]) + 1), path + '/' + dl,file_path_list)
    # for fl in fileList:
    #     # 打印文件
    #     # print('-' * (int(dirList[0])), fl)
    #     # 随便计算一下有多少个文件
    #     allFileNum = allFileNum + 1
    return file_path_list

def classificFileByNumber(file_path_list):
    dict = {}
    for i in range(len(file_path_list)):
        values = dict.get(file_path_list[i][1])
        if values is None:
            new_values = []
            dict[file_path_list[i][1]] = new_values
            values = new_values
        values.append(file_path_list[i][0])
    return dict

def classificFileByKinds(dict):
    big_dict = {}
    mcs = []
    keys = list(dict.keys())
    for i in range(len(keys)):
        identifier = keys[i]
        merchandise = re.findall('^[a-zA-Z]+',identifier)
        commodity = merchandise.pop(0)
#        commodity = commodity.lower()
        mc = []
        mc.append(identifier)
        mc.append(commodity)
        mcs.append(mc)
        number = identifier[len(commodity):len(identifier)]

    for i in range(len(mcs)):
        values = big_dict.get(mcs[i][1])
        if values is None:
            new_values = {}
            big_dict[mcs[i][1]] = new_values
            values = new_values
        values[mcs[i][0]] = dict.get(mcs[i][0])
    return big_dict

def file_dict(file_dir):
    file_path_list = dirFilePath(1, file_dir)
    dict = classificFileByNumber(file_path_list)
    big_dict = classificFileByKinds(dict)
    return big_dict
# if __name__ == '__main__':
#     big_dict = file_dict(cf.train_dir)
#     print('总文件数 =')

import sys
import os
import datetime
import time
from os.path import join

######################################################################
# Exceptions.

class NotDirectory(Exception):
    pass

######################################################################
# Functions.

def getlsize(path):
    return os.lstat(path)[6]

def getlmtime(path):
    return os.lstat(path)[8]

def file_type(filepath):
    if os.path.islink(filepath):
        return 'link'
    if os.path.isfile(filepath):
        return 'file'
    if os.path.isdir(filepath):
        return 'dir'
    return 'special'

# These three always show the directories first.

def cmp_filespec_name(a, b):
    if a['type'] == 'dir' and b['type'] != 'dir':
        return -1
    if b['type'] == 'dir' and a['type'] != 'dir':
        return 1
    return cmp(a['name'], b['name'])

def cmp_filespec_size(a, b):
    if a['type'] == 'dir' and b['type'] != 'dir':
        return -1
    if b['type'] == 'dir' and a['type'] != 'dir':
        return 1
    return cmp(a['size'], b['size'])

def cmp_filespec_mtime(a, b):
    if a['type'] == 'dir' and b['type'] != 'dir':
        return -1
    if b['type'] == 'dir' and a['type'] != 'dir':
        return 1
    return cmp(a['mtime'], b['mtime'])

filespec_cmp = {
    'name' : cmp_filespec_name,
    'size' : cmp_filespec_size,
    'mtime' : cmp_filespec_mtime
}

def make_filespec(path, name=False):
    if not name:
        name = os.path.basename(path)
    return {
        'name' : name,
        'path' : path,
        'type' : file_type(path),
        'size' : getlsize(path),
        'mtime' : getlmtime(path)
    }

# os.path.islink
# os.path.isdir
# os.path.isfile
def get_dir_contents(dir, sort_by="name", parent=True):
    if not os.path.isdir(dir):
        raise NotDirectory("%s is not a directory." % ( dir ))

    dir_contents = []
    try:
        dir_contents = os.listdir(dir)
    except OSError, e:
        pass
    contents = []
    for fname in dir_contents:
        abspath = os.path.abspath(os.path.join(dir, fname))
        contents.append(make_filespec(abspath))

    contents.sort(filespec_cmp[sort_by])

    if parent:
        parent_dir_path = os.path.abspath(os.path.join(dir, '..'))
        parent_dir = make_filespec(parent_dir_path, name="Up to higher level directory")
        contents.insert(0, parent_dir)

    return contents


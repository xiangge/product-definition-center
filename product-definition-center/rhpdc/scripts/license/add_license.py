#! /usr/bin/env python
import fileinput
import sys
import os
from optparse import OptionParser

SHEBANG_LINE = "#! /usr/bin/env python".replace(" ", "")
UTF_8_LINE = "# -*- coding: utf-8 -*-".replace(" ", "")
EXTENSION = ('.py', )


def add_license_content(new_license, f=None):
    if not f:
        # set f default as sys.stdout in method definition can't work correctly for file input.
        f = sys.stdout
    for line in open(new_license):
        f.write(line)


def read_file_content(file_path):
    with open(file_path, "r") as f:
        return f.read()


def compact_line(line):
    return line.replace(" ", "").rstrip("\n\r").lower()


def add_license_content_to_file(file_path, new_license):
    have_shebang = False
    have_utf_8 = False
    for line in open(file_path):
        compacted_line = compact_line(line)
        if compacted_line == SHEBANG_LINE:
            have_shebang = True
        if compacted_line == UTF_8_LINE:
            have_utf_8 = True

    empty_file = True

    for i, line in enumerate(fileinput.input(file_path, inplace=True)):
        empty_file = False
        compacted_line = compact_line(line)
        if i == 0 and not have_shebang and not have_utf_8:
            add_license_content(new_license)
        sys.stdout.write(line)
        if (have_utf_8 and compacted_line == UTF_8_LINE) or\
                (have_shebang and not have_utf_8 and compacted_line == SHEBANG_LINE):
            add_license_content(new_license)

    if empty_file:
        with open(file_path, "a") as f:
            add_license_content(new_license, f)


def is_qualified_file(filename):
    return filename.endswith(EXTENSION)


def replace_file_content(file_path, file_content, new_license, old_license):
    new_file_content = file_content.replace(read_file_content(old_license), read_file_content(new_license))
    with open(file_path, "w") as f:
        f.write(new_file_content)


def add_or_replace_content_to_file(file_path, new_license, old_license):
    file_content = read_file_content(file_path)
    if old_license and read_file_content(old_license) in file_content:
        print "Replacing license content in ", file_path
        replace_file_content(file_path, file_content, new_license, old_license)
    else:
        print "Adding license content to ", file_path
        add_license_content_to_file(file_path, new_license)


def add_license_content_to_dir(directory, new_license, old_license, recursive, all_files):
    for root, sub_dirs, files in os.walk(directory):
        for filename in files:
            if all_files or is_qualified_file(filename):
                file_path = os.path.join(root, filename)
                add_or_replace_content_to_file(file_path, new_license, old_license)
        if not recursive:
            break


if __name__ == '__main__':
    usage = """%prog -a <license_file> -d <directory> -R
       %prog -a <new_license_file> -r <old_license_file> -d <directory> -R
       %prog -a <new_license_file> -r <old_license_file> -d <directory> -A"""
    parser = OptionParser(usage)
    parser.add_option("-a", "--add", help="the license file whose content will be added to destination files",
                      dest='new_license')
    parser.add_option("-r", "--replace", help="the license file whose content will be replaced in destination files",
                      dest='old_license')
    parser.add_option("-d", "--directory", help="the destination directory", dest='dest_dir')
    parser.add_option("-R", action="store_true", help="recursively for the directory", dest="recursive", default=False)
    parser.add_option("-A", action="store_true", dest='all',
                      help="all files under the directory, but assuming they are python files",
                      default=False)
    options, args = parser.parse_args()

    if not options.new_license or not os.path.exists(options.new_license):
        parser.error("New license file not given or doesn't exist")
    if options.old_license and not os.path.exists(options.old_license):
        parser.error("Old license file doesn't exist")
    if not options.dest_dir or not os.path.isdir(options.dest_dir):
        parser.error("Destination directory is not given or doesn't exist")

    add_license_content_to_dir(options.dest_dir, options.new_license, options.old_license, options.recursive,
                               options.all)

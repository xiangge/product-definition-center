#
# Copyright (c) 2015-2017 Red Hat
# Licensed under The MIT License (MIT)
# http://opensource.org/licenses/MIT
#
import os
import subprocess

VERSION = "1.9.0-2"

# NOTE(xchu): use `git describe` when under git repository.
if os.system('git rev-parse 2> /dev/null > /dev/null') == 0:
    pipe = subprocess.Popen("git describe --match python-pdc-*",
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    label, err = pipe.communicate()
    label = label.replace('python-pdc-', '')
    # We follow semantic versioning to add annotated tags, so the
    # label here can be:
    #     0.1.0                # release tag,
    # or  0.1.0-s5             # pre-release tag with sprint metadata,
    # or  0.1.0-s5-2-gabcdefg  # devel build with 2 commits ahead the latest tag
    #                            with 'g'it short hash('abcdefg') metadata.
    # (more info: http://git-scm.com/docs/git-describe)
    #
    # But only one dash should be used here, so we need to replace other deshes
    # with dot if they exists.
    version_list = label.strip().split('-', 1)
    if len(version_list) == 1:
        VERSION = version_list[0]
    else:
        VERSION = version_list[0] + '-' + version_list[1].replace('-', '.')


def get_version():
    """
    Get PDC version info
    """
    return VERSION

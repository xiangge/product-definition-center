#!/bin/sh

set -ex

export DJANGO_SETTINGS_MODULE=rhpdc.settings

# import real data samples
export PYTHONPATH=$(pwd)/:$PYTHONPATH
time python ./_test_data/import_release.py
time python ./_test_data/import_images.py
time python ./_test_data/import_rpms.py
time python ./_test_data/import_repos.py
time python ./_test_data/clone_update_releases.py
time python ./_test_data/import_qe_owners_from_CYP.py
time python ./_test_data/import_package_owners_from_rhel_7_git.py
time python ./_test_data/import_with_verify_dist_git_url.py
time python ./_test_data/import_predefined_group_permissions.py

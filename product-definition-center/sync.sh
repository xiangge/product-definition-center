#!/bin/bash

set -xeu
export PYTHONPATH=$(pwd)/:${PYTHONPATH:-}

# remove old db
database=$(python _test_data/find_sqlite_db.py)
if [ -f "$database" ]; then
    rm -f "$database"
fi

# create new db
python manage.py migrate --noinput --settings=rhpdc.settings

# import real data samples
time python ./_test_data/import_release.py
time python ./_test_data/import_images.py
time python ./_test_data/import_rpms.py
time python ./_test_data/import_repos.py
time python ./_test_data/clone_update_releases.py
time python ./_test_data/import_qe_owners_from_CYP.py
time python ./_test_data/import_package_owners_from_rhel_7_git.py
time python ./_test_data/import_with_verify_dist_git_url.py
time python ./_test_data/import_predefined_group_permissions.py

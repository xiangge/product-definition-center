#! /bin/bash

set -e

PDC_DIR=$1
if [ $PDC_DIR ]; then
    CHECKOUT=$PDC_DIR
else
    CHECKOUT="/tmp/product-definition-center-upstream-checkout"
fi

GITHUB="https://github.com/product-definition-center/product-definition-center.git"

OLD_PWD=$(pwd)

if [ ! -d "$CHECKOUT/.git" ]; then
    # No previous checkout, clone from GitHub.
    git clone "$GITHUB" "$CHECKOUT"
    pushd "$CHECKOUT"
else
    # We have previous checkout, just download changes.
    pushd "$CHECKOUT"
    git fetch origin master --tags
    git reset --hard FETCH_HEAD
fi

# Make sure there are no extra files.
git clean -fd

# setup.py with change all dashes in version but the first to dots, so this
# line will replicate that.
VERSION=$(git describe --match "python-pdc-*" | sed -e "s/python-pdc-//" -e "s/-/./2g")

# Replace the version number in source code.
sed -i "s/^VERSION .*/VERSION = \"$VERSION\"/" pdc/__init__.py

# Create a tarball with setup.py.
rm -rf dist
python setup.py sdist

# The created tarball has name in version. We need to rename to name that works
# with the rest of build scripts. It is not enough to just rename the file, we
# also need to change the name of folder to which the tarball will unpack.
pushd dist
# Unpack created tarball.
tar xf pdc-"$VERSION".tar.gz
# Rename the folder.
mv "pdc-$VERSION" product-definition-center-upstream
# Recreate tarball in target destination, this time with proper name and
# contents.
mkdir -p "$OLD_PWD/dist"
tar cvf "$OLD_PWD/dist/product-definition-center-upstream.tar.gz" product-definition-center-upstream/

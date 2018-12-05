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
    git checkout release
else
    # We have previous checkout, just download changes.
    pushd "$CHECKOUT"
    git fetch origin release --tags
    git checkout release
    git reset --hard FETCH_HEAD
fi

# Make sure there are no extra files.
git clean -fd

TAG=$(git describe --abbrev=0 --match "python-pdc-*")
ARCHIVE="$TAG.tar.gz"
URL="https://github.com/product-definition-center/product-definition-center/archive/$ARCHIVE"
echo "Getting $URL ...."
wget "$URL"
# Unpack downloaded archive.
tar xf "$ARCHIVE"
# Rename the folder.
mv -v "product-definition-center-$TAG" product-definition-center-upstream
# Recreate tarball in target destination, this time with proper name and
# contents.
mkdir -p "$OLD_PWD/dist"
tar cvf "$OLD_PWD/dist/product-definition-center-upstream.tar.gz" product-definition-center-upstream/

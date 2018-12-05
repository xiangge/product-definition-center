#!/bin/bash
# Creates new package release in git.

set -e
set -o pipefail

PDC_UPSTREAM_DIR=${PDC_UPSTREAM_DIR:-"/tmp/product-definition-center-upstream-checkout"}
PDC_UPSTREAM_REPO="https://github.com/product-definition-center/product-definition-center.git"

fail() {
    echo "Error: $*" 1>&2
    exit 1
}

# Print changelog for current repository and upstream repo.
# Argument is upstream tag.
changelog() {
    tag=$1
    last_tag=$(git describe --tags --abbrev=0 --match='python-pdc-*')
    git log --pretty='- [rhpdc] %s (%ae)' "$last_tag..HEAD"

    if [ ! -d "$PDC_UPSTREAM_DIR" ]; then
        git clone "$PDC_UPSTREAM_REPO" "$PDC_UPSTREAM_DIR"
    fi

    (
        cd "$PDC_UPSTREAM_DIR"
        git fetch origin release --tags
        git checkout "$tag"
        rpm -q --specfile pdc.spec --queryformat '%{CHANGELOGTEXT}'
    )
}

if ! git diff --quiet; then
    fail 'Make sure you have no uncommitted changes in your repository.'
fi

current_branch=$(git rev-parse --abbrev-ref HEAD)
if [[ "$current_branch" != "release" ]]; then
    fail 'Current git branch should be "release".'
fi

echo "Current git commit is: $(git describe)"


read -p 'Enter new version (e.g. "1.8.0"): ' version
if [[ ! "$version" =~ ^[1-9][0-9]*\.[0-9]+\.[0-9]+$ ]]; then
    fail 'Unexpected version format.'
fi

read -p 'Enter new release number: ' release
if [[ ! "$release" =~ ^[1-9][0-9]*$ ]]; then
    fail 'Unexpected release format.'
fi

sed -i 's/\(^%define default_version \).*/\1'"$version"'/' pdc.spec
sed -i 's/\(^%define default_release \).*/\1'"$release"'/' pdc.spec
sed -i 's/\(^VERSION = \)".*/\1"'"$version-$release"'"/' rhpdc/__init__.py

git add rhpdc/__init__.py
tito tag --keep-version \
    --changelog="$(changelog "python-pdc-$version-$release")"


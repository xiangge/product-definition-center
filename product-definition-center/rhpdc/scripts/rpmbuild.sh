#!/bin/bash

set -e

mypath=$(cd "$( dirname "${BASH_SOURCE[0]}")/.." && pwd)
topdir=$(dirname $mypath)
spec_file="$topdir/pdc.spec"

if [ $# -eq 0 ] ; then
    echo "Usage: $0 <rpmbuild-options...>" >&2
    echo " - Note: RPM spec file is pointed to '$spec_file' by default and no necessary to be specified"
    exit 1
fi

recent_tag="$(git describe --abbrev=0 --match "python-pdc-*" | sed "s/python-pdc-//")"
long_describe="$(git describe --match "python-pdc-*" | sed "s/python-pdc-//")"
recent_version=${recent_tag%%-*}
recent_release=${recent_tag#*-}
version=$recent_version
git_suffix="${long_describe#$recent_tag}"
release="${recent_release}${git_suffix//-/.}"

rpmbuild \
    --define "version $version" \
    --define "release $release" \
    --define "_release_ $release" \
    "$@" $spec_file

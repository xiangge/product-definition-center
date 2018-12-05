#!/bin/bash
# This bash is used for building src.
# pre-build.sh <dist-git branch> <srpm url> <commit message> <execute folder> <project name>
#

set -e
if [[ -z "$5" || ! -z "$6" ]];then
  echo "please input four parameters"
  echo "pre-build.sh <branch dist-git> <srpm url> <commit message> <execute folder> <project name>"
  exit 1
fi
cd "$4"
rhpkg clone "$5"
cd "$5"
rhpkg switch-branch "$1"
rhpkg import "$2"
rhpkg commit -m "$3"
#rhpkg push
#rhpkg build --scratch

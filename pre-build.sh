#!/bin/bash
# This bash is used for building src.
# pre-build.sh <branch of disgit> <srpm url> <commit message>
#
if [[ -z "$3" || ! -z "$4" ]];then
  echo "please input three parameters"
  echo "pre-build.sh <branch of disgit> <srpm url> <commit message>"
  exit 1
fi
rhpkg clone python-pdc
rhpkg switch-branch $1
rhpkg import $2
rhpkg commit -m $3
rhpkg build --scratch

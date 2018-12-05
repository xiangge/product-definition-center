#!/bin/bash
# This bash is used for checking the build env.

set -e
system_info=`cat /etc/redhat-release`

if [[ "$system_info" =~ "Fedora" ]];then
  echo Current system is fedora ...
  if [[ ! -f "/etc/yum.repos.d/rhpkg.repo" ]];then
    sudo wget -P /etc/yum.repos.d http://download.devel.redhat.com/rel-eng/dist-git/fedora/rhpkg.repo
  fi
elif [[ "$system_info" =~ "Red" ]];then
  echo Current system is rhel ...
  if [[ ! -f "/etc/yum.repos.d/rhpkg.repo" ]];then
    sudo wget -P /etc/yum.repos.d http://download.devel.redhat.com/rel-eng/dist-git/rhel/rhpkg.repo
  fi
else
   echo please build with rhel or fedora
   exit 1
fi

sudo yum install rpm-build rpmdevtools
sudo yum install rhpkg
sudo yum install tito

#!/bin/bash
# This bash is used for checking the build env.

system_info=`cat /etc/redhat-release`

if [[ "$system_info" =~ "Fedora" ]];then
  echo Current system is fedora ...
  sudo curl -o /etc/yum.repos.d/rhpkg.repo http://download.devel.redhat.com/fedora/dist-git/rhel/rhpkg.repo
elif [[ $system_info =~ "Red" ]];then
  echo Current system is Redhat
  sudo curl -o /etc/yum.repos.d/rhpkg.repo http://download.devel.redhat.com/rel-eng/dist-git/rhel/rhpkg.repo
else
   echo please use other system
   exit 1
fi

sudo yum install rpm-build rpmdevtools
sudo yum install rhpkg
sudo yum install tito


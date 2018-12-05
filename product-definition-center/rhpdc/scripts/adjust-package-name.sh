#!/bin/bash
# Adjust package name created by setup.py.
# E.g. "pdc-1.8.0.post1.tar.bz2" becomes "pdc-1.8.0-1.tar.bz2".
set -e
set -o pipefail

(
    cd dist

    # allow * to expand to nothing
    shopt -s nullglob

    for src_file in *.post*.tar.bz2; do
        src_dir="${src_file%.tar.bz2}"
        dest_file="${src_file/.post/-}"
        dest_dir="${dest_file%.tar.bz2}"
        tar vxjf "$src_file"
        mv -v "$src_dir" "$dest_dir"
        rm -vf "$src_file"
        tar vcjf "$dest_file" "$dest_dir"
        rm -vrf "$dest_dir"
    done
)

#!/usr/bin/python


import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rhpdc.settings")
django.setup()

from pdc.apps.compose.lib import compose__import_rpms
from import_request import ImportRequest


request = ImportRequest()

compose__import_rpms(request,
                     "rhel-7.0",
                     json.load(open("_test_data/composes/rhel-7.0/composeinfo.json", "r")),
                     json.load(open("_test_data/composes/rhel-7.0/rpm-manifest.json", "r")))

compose__import_rpms(request,
                     "rhel-7.1",
                     json.load(open("_test_data/composes/rhel-7.1/composeinfo.json", "r")),
                     json.load(open("_test_data/composes/rhel-7.1/rpm-manifest.json", "r")))

compose__import_rpms(request,
                     "rhel-7.1",
                     json.load(open("_test_data/composes/rhel-7.1-nightly/composeinfo.json", "r")),
                     json.load(open("_test_data/composes/rhel-7.1-nightly/rpm-manifest.json", "r")))

compose__import_rpms(request,
                     "rhel-le-7.1",
                     json.load(open("_test_data/composes/rhel-le-7.1/composeinfo.json", "r")),
                     json.load(open("_test_data/composes/rhel-le-7.1/rpm-manifest.json", "r")))

compose__import_rpms(request,
                     "rhscl-1.2@rhel-6",
                     json.load(open("_test_data/composes/rhscl-1.2-rhel-6/composeinfo.json", "r")),
                     json.load(open("_test_data/composes/rhscl-1.2-rhel-6/rpm-manifest.json", "r")))

compose__import_rpms(request,
                     "rhscl-1.2@rhel-7",
                     json.load(open("_test_data/composes/rhscl-1.2-rhel-7/composeinfo.json", "r")),
                     json.load(open("_test_data/composes/rhscl-1.2-rhel-7/rpm-manifest.json", "r")))

compose__import_rpms(request,
                     "satellite-6.0.4@rhel-5",
                     json.load(open("_test_data/composes/satellite-6.0.4-rhel-5/composeinfo.json", "r")),
                     json.load(open("_test_data/composes/satellite-6.0.4-rhel-5/rpm-manifest.json", "r")))

compose__import_rpms(request,
                     "satellite-6.0.4@rhel-6",
                     json.load(open("_test_data/composes/satellite-6.0.4-rhel-6/composeinfo.json", "r")),
                     json.load(open("_test_data/composes/satellite-6.0.4-rhel-6/rpm-manifest.json", "r")))

compose__import_rpms(request,
                     "satellite-6.0.4@rhel-7",
                     json.load(open("_test_data/composes/satellite-6.0.4-rhel-7/composeinfo.json", "r")),
                     json.load(open("_test_data/composes/satellite-6.0.4-rhel-7/rpm-manifest.json", "r")))

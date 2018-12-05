#!/usr/bin/python


import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rhpdc.settings")
django.setup()

from pdc.apps.compose.lib import compose__import_images
from import_request import ImportRequest


request = ImportRequest()

compose__import_images(request,
                       "rhel-7.0",
                       json.load(open("_test_data/composes/rhel-7.0/composeinfo.json", "r")),
                       json.load(open("_test_data/composes/rhel-7.0/image-manifest.json", "r")))

compose__import_images(request,
                       "rhel-7.1",
                       json.load(open("_test_data/composes/rhel-7.1-nightly/composeinfo.json", "r")),
                       json.load(open("_test_data/composes/rhel-7.1-nightly/image-manifest.json", "r")))

compose__import_images(request,
                       "rhscl-1.2@rhel-6",
                       json.load(open("_test_data/composes/rhscl-1.2-rhel-6/composeinfo.json", "r")),
                       json.load(open("_test_data/composes/rhscl-1.2-rhel-6/image-manifest.json", "r")))

compose__import_images(request,
                       "rhscl-1.2@rhel-7",
                       json.load(open("_test_data/composes/rhscl-1.2-rhel-7/composeinfo.json", "r")),
                       json.load(open("_test_data/composes/rhscl-1.2-rhel-7/image-manifest.json", "r")))

compose__import_images(request,
                       "satellite-6.0.4@rhel-5",
                       json.load(open("_test_data/composes/satellite-6.0.4-rhel-5/composeinfo.json", "r")),
                       json.load(open("_test_data/composes/satellite-6.0.4-rhel-5/image-manifest.json", "r")))

compose__import_images(request,
                       "satellite-6.0.4@rhel-6",
                       json.load(open("_test_data/composes/satellite-6.0.4-rhel-6/composeinfo.json", "r")),
                       json.load(open("_test_data/composes/satellite-6.0.4-rhel-6/image-manifest.json", "r")))

compose__import_images(request,
                       "satellite-6.0.4@rhel-7",
                       json.load(open("_test_data/composes/satellite-6.0.4-rhel-7/composeinfo.json", "r")),
                       json.load(open("_test_data/composes/satellite-6.0.4-rhel-7/image-manifest.json", "r")))

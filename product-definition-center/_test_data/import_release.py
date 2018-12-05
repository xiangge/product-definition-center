#!/usr/bin/python


import os
import json
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rhpdc.settings")
django.setup()

from pdc.apps.release import lib
from import_request import ImportRequest


request = ImportRequest()
data = json.load(open("_test_data/composes/rhel-7.0/composeinfo.json", "r"))
lib.release__import_from_composeinfo(request, data)

data = json.load(open("_test_data/composes/rhel-7.1/composeinfo.json", "r"))
lib.release__import_from_composeinfo(request, data)

data = json.load(open("_test_data/composes/rhel-le-7.1/composeinfo.json", "r"))
lib.release__import_from_composeinfo(request, data)

data = json.load(open("_test_data/composes/supp-7.0/composeinfo.json", "r"))
lib.release__import_from_composeinfo(request, data)

data = json.load(open("_test_data/composes/dp-1.0/composeinfo.json", "r"))
lib.release__import_from_composeinfo(request, data)

data = json.load(open("_test_data/composes/rhscl-1.2-rhel-6/composeinfo.json", "r"))
lib.release__import_from_composeinfo(request, data)

data = json.load(open("_test_data/composes/rhscl-1.2-rhel-7/composeinfo.json", "r"))
lib.release__import_from_composeinfo(request, data)

data = json.load(open("_test_data/composes/satellite-6.0.4-rhel-5/composeinfo.json", "r"))
lib.release__import_from_composeinfo(request, data)

data = json.load(open("_test_data/composes/satellite-6.0.4-rhel-6/composeinfo.json", "r"))
lib.release__import_from_composeinfo(request, data)

data = json.load(open("_test_data/composes/satellite-6.0.4-rhel-7/composeinfo.json", "r"))
lib.release__import_from_composeinfo(request, data)

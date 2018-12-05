#!/usr/bin/python

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rhpdc.settings")
django.setup()

from django.conf import settings

if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    print settings.DATABASES['default']['NAME']

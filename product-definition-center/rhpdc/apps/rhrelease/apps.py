#
# Copyright (c) 2015-2017 Red Hat
# Licensed under The MIT License (MIT)
# http://opensource.org/licenses/MIT
#
from django.apps import AppConfig


class ReleaseConfig(AppConfig):
    name = 'rhpdc.apps.rhrelease'

    def ready(self):
        from . import views
        views.extend_docstrings()
        views.extend_product_serializer()

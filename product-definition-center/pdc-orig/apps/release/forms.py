# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 Red Hat
# Licensed under The MIT License (MIT)
# http://opensource.org/licenses/MIT
#


import django.forms as forms
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _


class ReleaseSearchForm(forms.Form):
    search      = forms.CharField(required=False)
    disabled    = forms.BooleanField(required=False, label=_('Search in disabled releases'))

    def get_query(self, request):
        self.is_valid()
        search = self.cleaned_data["search"]
        disabled = self.cleaned_data["disabled"]  # noqa

        query = Q()

        if search:
            query |= Q(short__icontains=search)
            query |= Q(version__icontains=search)
            query |= Q(name__icontains=search)
            query |= Q(release_id__icontains=search)

        # TODO: disabled

        return query


class BaseProductSearchForm(forms.Form):
    search = forms.CharField(required=False)

    def get_query(self, request):
        self.is_valid()
        search = self.cleaned_data["search"]

        query = Q()

        if search:
            query |= Q(short__icontains=search)
            query |= Q(version__icontains=search)
            query |= Q(name__icontains=search)

        # TODO: disabled

        return query


class ProductSearchForm(forms.Form):
    search = forms.CharField(required=False)

    def get_query(self, request):
        self.is_valid()
        search = self.cleaned_data["search"]

        query = Q()

        if search:
            query |= Q(name__icontains=search)
            query |= Q(short__icontains=search)

        return query


class ProductVersionSearchForm(forms.Form):
    search = forms.CharField(required=False)

    def get_query(self, request):
        self.is_valid()
        search = self.cleaned_data["search"]

        query = Q()

        if search:
            query |= Q(name__icontains=search)
            query |= Q(short__icontains=search)
            query |= Q(version__icontains=search)

        return query

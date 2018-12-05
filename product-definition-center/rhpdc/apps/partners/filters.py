# -*- coding: utf-8 -*-
#
# Copyright (c) 2015-2017 Red Hat
# Licensed under The MIT License (MIT)
# http://opensource.org/licenses/MIT
#
import django_filters

from pdc.apps.common import filters
from . import models


class PartnerFilterSet(django_filters.FilterSet):
    enabled = filters.CaseInsensitiveBooleanFilter()
    binary = filters.CaseInsensitiveBooleanFilter()
    source = filters.CaseInsensitiveBooleanFilter()
    name = django_filters.CharFilter(lookup_type='icontains')
    type = django_filters.CharFilter(name='type__name')
    short = filters.MultiValueFilter(name='short')
    ftp_dir = filters.MultiValueFilter(name='ftp_dir')
    rsync_dir = filters.MultiValueFilter(name='rsync_dir')
    compose_arches = filters.MultiValueFilter(name='compose_arches__name')
    errata_packages = filters.MultiValueFilter(name='errata_packages__name')

    class Meta:
        model = models.Partner
        fields = (
            'short',
            'name',
            'type',
            'enabled',
            'binary',
            'source',
            'ftp_dir',
            'rsync_dir',
            'compose_arches',
            'errata_packages',
        )


class PartnerMappingFilterSet(django_filters.FilterSet):
    partner = filters.MultiValueFilter(name='partner__short')
    release = filters.MultiValueFilter(name='variant_arch__variant__release__release_id')
    variant = filters.MultiValueFilter(name='variant_arch__variant__variant_uid')
    arch = filters.MultiValueFilter(name='variant_arch__arch__name')

    class Meta:
        model = models.PartnerMapping
        fields = ('partner', 'release', 'variant', 'arch')

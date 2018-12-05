#
# Copyright (c) 2015 Red Hat
# Licensed under The MIT License (MIT)
# http://opensource.org/licenses/MIT
#
import django_filters as filters

from pdc.apps.common.filters import MultiValueFilter, MultiIntFilter, CaseInsensitiveBooleanFilter
from . import models


class RepoFilter(filters.FilterSet):
    arch = MultiValueFilter(name='variant_arch__arch__name')
    content_category = MultiValueFilter(name='content_category__name')
    content_format = MultiValueFilter(name='content_format__name')
    release_id = MultiValueFilter(name='variant_arch__variant__release__release_id')
    variant_uid = MultiValueFilter(name='variant_arch__variant__variant_uid')
    repo_family = MultiValueFilter(name='repo_family__name')
    service = MultiValueFilter(name='service__name')
    shadow = CaseInsensitiveBooleanFilter()
    product_id = MultiIntFilter()
    name = MultiValueFilter(name='name')

    class Meta:
        model = models.Repo
        fields = ('arch', 'content_category', 'content_format', 'name', 'release_id',
                  'repo_family', 'service', 'shadow', 'variant_uid', 'product_id')


class RepoFamilyFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_type="icontains")

    class Meta:
        model = models.RepoFamily
        fields = ('name',)

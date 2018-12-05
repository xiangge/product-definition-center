# NOTE it is important not to import any filters module from other apps. Doing
# that could cause cyclic imports and break the application.
from pdc.apps.common.filters import NullableCharFilter, MultiIntFilter, CaseInsensitiveBooleanFilter, MultiValueFilter


def add_filter(filter_class, field_name, field):
    filter_class.base_filters[field_name] = field
    if hasattr(filter_class, 'Meta') and hasattr(filter_class.Meta, 'fields'):
        filter_class.Meta.fields = filter_class.Meta.fields + (field_name, )


def extend_release_filter(release_filter):
    add_filter(release_filter, 'brew_default_target',
               NullableCharFilter(name='brew_mapping__default_target'))
    add_filter(release_filter, 'brew_allowed_tag',
               MultiValueFilter(name='brew_mapping__allowed_tags__tag_name'))
    add_filter(release_filter, 'product_pages_release_id',
               MultiIntFilter(name='product_pages_link__product_pages_id'))
    add_filter(release_filter, 'errata_product_version',
               NullableCharFilter(name='errata__product_version'))


class ProductInternalFlagFilter(CaseInsensitiveBooleanFilter):

    def filter(self, qs, value):
        if not value:
            return qs
        self._validate_boolean(value)
        if value.lower() in self.TRUE_STRINGS:
            # internal flag is true
            qs = qs.filter(**{'internal__isnull': False})
        elif value.lower() in self.FALSE_STRINGS:
            qs = qs.filter(**{'internal__isnull': True})
        else:
            qs = qs.none()
        return qs


def extend_product_filter(product_filter):
    add_filter(product_filter, 'internal', ProductInternalFlagFilter())

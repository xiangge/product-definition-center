#
# Copyright (c) 2015 Red Hat
# Licensed under The MIT License (MIT)
# http://opensource.org/licenses/MIT
#
from collections import OrderedDict
import logging
import re
import sys
import json

from django.conf import settings
from django.utils.encoding import smart_text

from contrib import drf_introspection

from django.db.models.fields import NOT_PROVIDED
from django.core.urlresolvers import NoReverseMatch
from django.core.exceptions import FieldDoesNotExist
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.utils import formatting
from rest_framework.reverse import reverse
from rest_framework import serializers, relations, fields

from pdc.apps.utils.utils import urldecode

"""
## Writing documentation in docstrings

Docstrings of each method will be available in browsable API as documentation.
These features are available to simplify writing the comments:

 * the content is formatted as Markdown
 * %(HOST_NAME)s and %(API_ROOT)s macros will be replaced by host name and URL
   fragment for API, respectively
 * %(FILTERS)s will be replaced a by a list of available query string filters
 * %(SERIALIZER)s will be replaced by a code block with details about
   serializer
 * %(WRITABLE_SERIALIZER)s will do the same, but without read-only fields
 * $URL:route-name:arg1:arg2...$ will be replaced by absolute URL
 * $LINK:route-name:arg1:...$ will be replaced by a clickable link with
   relative URL pointing to the specified place; arguments for LINK will be
   wrapped in braces automatically

When the URL specification can not be resolve, "BAD URL" will be displayed on
the page and details about the error will be logged to the error log.
"""


PDC_APIROOT_DOC = """
The REST APIs make it possible to programmatic access the data in Product Definition Center(a.k.a. PDC).

Create new Product, import rpms and query components with contact informations, and more.

The REST API identifies users using Token which will be generated for all authenticated users.

**Please remember to use your token as HTTP header for every requests that need authentication.**

If you want to record the reason for change, you can add Header (-H "PDC-Change-Comment: reasonforchange") in request.

Responses are available in JSON format.

**NOTE:** in order to use secure HTTPS connections, you'd better to add server's certificate as trusted.

"""

URL_SPEC_RE = re.compile(r'\$(?P<type>URL|LINK):(?P<details>[^$]+)\$')
ORDERING_STRING = "\n * `ordering` is used to override the ordering of the results, the value could be: "
ORDERING_STRING_NESTED = "The nested ordering is supported by using double underscore \_\_ ."


class ReadOnlyBrowsableAPIRenderer(BrowsableAPIRenderer):
    template = "browsable_api/api.html"
    methods_mapping = (
        'list',
        'retrieve',
        'create',
        'bulk_create',
        'update',
        'destroy',
        'bulk_destroy',
        'partial_update',

        'bulk_update',
        # Token Auth methods
        'obtain',
        'refresh',
    )

    def get_raw_data_form(self, data, view, method, request):
        return None

    def get_rendered_html_form(self, data, view, method, request):
        return None

    def get_context(self, data, accepted_media_type, renderer_context):
        self.request = renderer_context['request']
        super_class = super(ReadOnlyBrowsableAPIRenderer, self)
        super_retval = super_class.get_context(data, accepted_media_type,
                                               renderer_context)

        if super_retval is not None:
            del super_retval['put_form']
            del super_retval['post_form']
            del super_retval['delete_form']
            del super_retval['options_form']

            del super_retval['raw_data_put_form']
            del super_retval['raw_data_post_form']
            del super_retval['raw_data_patch_form']
            del super_retval['raw_data_put_or_patch_form']

            super_retval['display_edit_forms'] = False

            super_retval['version'] = "1.0"

            view = renderer_context['view']
            super_retval['overview'] = self.get_overview(view)

        return super_retval

    def get_overview(self, view):
        if view.__class__.__name__ == 'APIRoot':
            return self.format_docstring(None, None, PDC_APIROOT_DOC)
        overview = view.__doc__ or ''
        return self.format_docstring(view, '<overview>', overview)

    def get_description(self, view, *args):
        if view.__class__.__name__ == 'APIRoot':
            return ''

        description = OrderedDict()
        for method in self.methods_mapping:
            func = getattr(view, method, None)
            docstring = func and func.__doc__ or ''
            if docstring:
                description[method] = self.format_docstring(view, method, docstring)

        return description

    def format_docstring(self, view, method, docstring):
        macros = settings.BROWSABLE_DOCUMENT_MACROS
        if view:
            macros['FILTERS'] = get_filters(view)
            if 'list' == method:
                ordering_field = get_ordering_field(view, method)
                if ordering_field:
                    ordering_string = ORDERING_STRING + " %s . " % ordering_field + ORDERING_STRING_NESTED
                    macros['FILTERS'] += ordering_string
            if '%(SERIALIZER)s' in docstring:
                macros['SERIALIZER'] = get_serializer(view, include_read_only=True)
            if '%(WRITABLE_SERIALIZER)s' in docstring:
                macros['WRITABLE_SERIALIZER'] = get_serializer(view, include_read_only=False)
            if hasattr(view, 'docstring_macros'):
                macros.update(view.docstring_macros)
        string = formatting.dedent(docstring)
        formatted = string % macros
        formatted = self.substitute_urls(view, method, formatted)
        string = smart_text(formatted)
        return formatting.markup_description(string)

    def substitute_urls(self, view, method, text):
        def replace_url(match):
            type = match.groupdict()['type']
            parts = match.groupdict()['details'].split(':')
            url_name = parts[0]
            args = parts[1:]
            if type == 'LINK':
                args = ['{%s}' % arg for arg in args]
            try:
                if type == 'LINK':
                    url = reverse(url_name, args=args)
                    return '[`%s`](%s)' % (urldecode(url), url)
                return reverse(url_name, args=args, request=self.request)
            except NoReverseMatch:
                logger = logging.getLogger(__name__)
                logger.error('Bad URL specifier <%s> in %s.%s'
                             % (match.group(0), view.__class__.__name__, method),
                             exc_info=sys.exc_info())
                return 'BAD URL'
        return URL_SPEC_RE.sub(replace_url, text)


def get_ordering_field(view, method):
    """ If the APIs have the LIST method; for the view of LIST method, add the
    Ordering field for the users.
    """
    if 'list' in method and view.serializer_class:
        model_fields = [field.name for field in view.queryset.model._meta.fields]
        serializer_fields = [
            field.source or field_name
            for field_name, field in view.serializer_class().fields.items()
            if not getattr(field, 'write_only', False)]
        valid_fields = list(set(model_fields).intersection(set(serializer_fields)))
        return valid_fields
    else:
        return None


FILTERS_CACHE = {}
FILTER_DEFS = {
    'CharFilter': 'string',
    'NullableCharFilter': 'string | null',
    'BooleanFilter': 'bool',
    'CaseInsensitiveBooleanFilter': 'bool',
    'ActiveReleasesFilter': 'bool',
    'MultiIntFilter': 'int',
    'MultiValueRegexFilter': 'regular expression'
}
LOOKUP_TYPES = {
    'icontains': 'case insensitive, substring match',
    'contains': 'substring match',
    'iexact': 'case insensitive',
}


def get_filters(view):
    """
    For a given view set returns which query filters are available for it a
    Markdown formatted list. The list does not include query filters specified
    on serializer or query arguments used for paging.
    """
    if view in FILTERS_CACHE:
        return FILTERS_CACHE[view]

    allowed_keys = drf_introspection.get_allowed_query_params(view)
    filter_class = getattr(view, 'filter_class', None)
    filterset = filter_class() if filter_class is not None else None
    filterset_fields = filterset.filters if filterset is not None else []
    filter_fields = set(getattr(view, 'filter_fields', []))
    extra_query_params = set(getattr(view, 'extra_query_params', []))

    filters = []
    for key in sorted(allowed_keys):
        if key in filterset_fields:
            # filter defined in FilterSet
            filter = filterset_fields.get(key)
            filter_type = FILTER_DEFS.get(filter.__class__.__name__, 'string')
            lookup_type = LOOKUP_TYPES.get(filter.lookup_type)
            if lookup_type:
                lookup_type = ', %s' % lookup_type
            filters.append(' * `%s` (%s%s)' % (key, filter_type, lookup_type or ''))
        elif key in filter_fields or key in extra_query_params:
            # filter defined in viewset directly; type depends on model, not easily available
            filters.append(' * `%s`' % key)
        # else filter defined somewhere else and not relevant here (e.g.
        # serializer or pagination settings).
    filters = '\n'.join(filters)
    FILTERS_CACHE[view] = filters
    return filters


SERIALIZERS_CACHE = {}
SERIALIZER_DEFS = {
    'BooleanField': 'boolean',
    'NullBooleanField': 'boolean',
    'CharField': 'string',
    'IntegerField': 'int',
    'HyperlinkedIdentityField': 'url',
    'DateTimeField': 'datetime',
    'DateField': 'date',
    'StringRelatedField': 'string',
    'ReadOnlyField': 'data',
    'EmailField': 'email address',
    'SlugField': 'string',
    'URLField': 'url',
}


def _get_type_from_str(str, default=None):
    """
    Convert docstring into object suitable for inclusion as documentation. It
    tries to parse the docstring as JSON, falling back on provided default
    value.
    """
    if str:
        try:
            return json.loads(str)
        except ValueError:
            pass
    return default if default is not None else str


def _get_details_for_slug(serializer, field_name, field):
    """
    For slug field, we ideally want to get Model.field format. However, in some
    cases getting the model name is not possible, and only field name is
    displayed.
    """
    model = ''
    if hasattr(field, 'queryset') and field.queryset:
        model = field.queryset.model.__name__ + '.'
    return '%s%s' % (model, field.slug_field)


def get_field_type(serializer, field_name, field, include_read_only):
    """
    Try to describe a field type.
    """
    if isinstance(field, (relations.ManyRelatedField, serializers.ListSerializer)):
        # Many field, recurse on child and make it a list
        if isinstance(field, relations.ManyRelatedField):
            field = field.child_relation
        else:
            field = field.child
        return [get_field_type(serializer, field_name, field, include_read_only)]
    if field.__class__.__name__ in SERIALIZER_DEFS:
        return SERIALIZER_DEFS[field.__class__.__name__]
    elif isinstance(field, serializers.SlugRelatedField):
        return _get_details_for_slug(serializer, field_name, field)
    elif isinstance(field, serializers.SerializerMethodField):
        # For method fields try to use docstring of the method.
        method_name = field.method_name or 'get_{field_name}'.format(field_name=field_name)
        method = getattr(serializer, method_name, None)
        if method:
            docstring = getattr(method, '__doc__')
            return _get_type_from_str(docstring, docstring or 'method')
    elif not include_read_only and hasattr(field, 'writable_doc_format'):
        return _get_type_from_str(field.writable_doc_format)
    elif hasattr(field, 'doc_format'):
        return _get_type_from_str(field.doc_format)
    elif isinstance(field, serializers.BaseSerializer):
        return describe_serializer(field, include_read_only)
    logger = logging.getLogger(__name__)
    logger.error('Undocumented field %s' % field)
    return 'UNKNOWN'


def get_default_value(serializer, field_name, field):
    """
    Try to get default value for a field and format it nicely.
    """
    value = field.default
    if hasattr(value, 'doc_format'):
        return (value.doc_format
                if isinstance(value.doc_format, basestring)
                else str(value.doc_format))
    if value == fields.empty:
        # Try to get default from model field.
        try:
            default = serializer.Meta.model._meta.get_field(field_name).default
            return default if default != NOT_PROVIDED else None
        except (FieldDoesNotExist, AttributeError):
            return None
    return value


def describe_serializer(serializer, include_read_only):
    """
    Try to get description of a serializer. It tries to inspect all fields
    separately, if the serializer does not have fields, it falls back to
    `doc_format` class attribute (if present). If all fails, an error is
    logged.
    """
    data = {}
    if hasattr(serializer, 'get_fields'):
        for field_name, field in serializer.get_fields().iteritems():
            notes = []
            if field.read_only:
                notes.append('read-only')
                if not include_read_only:
                    continue
            elif not field.required:
                notes.append('optional')
                default = json.dumps(get_default_value(serializer, field_name, field))
                if not (default is None and field.allow_null):
                    notes.append('default=%s' % default)
            if field.allow_null:
                notes.append('nullable')
            notes = ' (%s)' % ', '.join(notes) if notes else ''
            data[field_name + notes] = get_field_type(serializer, field_name, field, include_read_only)
        return data
    elif hasattr(serializer.__class__, 'doc_format'):
        return serializer.doc_format
    else:
        logger = logging.getLogger(__name__)
        logger.error('Failed to get details for serializer %s' % serializer)
        return 'data'


def get_serializer(view, include_read_only):
    """
    For given view, return a Markdown code block with JSON description of the
    serializer. If `include_read_only` is `False`, only writable fields will be
    included.
    """
    if (view, include_read_only) in SERIALIZERS_CACHE:
        return SERIALIZERS_CACHE[(view, include_read_only)]
    if not hasattr(view, 'get_serializer'):
        return None
    try:
        serializer = view.get_serializer()
        desc = json.dumps(describe_serializer(serializer, include_read_only),
                          indent=4, sort_keys=True)
        doc = '\n'.join('    %s' % line for line in desc.split('\n'))
    except AssertionError:
        # Even when `get_serializer` is present, it may raise exception.
        doc = None
    SERIALIZERS_CACHE[(view, include_read_only)] = doc
    return doc

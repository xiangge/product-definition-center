#
# Copyright (c) 2015-2017 Red Hat
# Licensed under The MIT License (MIT)
# http://opensource.org/licenses/MIT
#


RELEASE_DOCS = {
    'update': """
        This end-point allows updating a release.

        When using the `PUT` method, if an optional field is not specified in
        the input, it will be erased.

        This applies also to Bugzilla, DistGit, Brew and Product Pages mapping:
        if it is not specified, it will be cleared.

        __Method__: PUT, PATCH

        __URL__: $LINK:release-detail:release_id$

        __Data__:

        %(WRITABLE_SERIALIZER)s

        Please note that if you change the `short`, `version`, `release_type`
        or `base_product` fields, the `release_id` will be updated and the URL
        of this release will change.

        For Brew mapping, it is possible to update only a part of the mapping
        with the `PATCH` method. If only `default_target` is specified, it will
        be stored as expected. If `allowed_tags` is specified, these tags will
        be set as currently allowed tags.

        There are two additional keys under `brew` for `PATCH` method: the tags
        in `add_allowed_tags` will be added as allowed tags (without deleting
        existing tags), tags from `remove_allowed_tags` will be deleted. These
        two keys can be used at the same time, but they can not be combined
        with `allowed_tags`.

        __Response__:

        %(SERIALIZER)s
    """,
}

CLONE_DOC = """
    Clone an existing release identified by `old_release_id`. Currently the
    release, its variants and arches will be cloned. Also, all release
    components associated with the release will be cloned.

    __Method__: POST

    __URL__: $LINK:releaseclone-list$

    __Data__:

        {
            "old_release_id":               string,
            "short":                        string,     # optional
            "version":                      string,     # optional
            "name":                         string,     # optional
            "release_type":                 string,     # optional
            "base_product":                 string,     # optional
            "active":                       bool,       # optional
            "product_version":              string,     # optional
            "dist_git": {
                "branch":                   string
            },                                          # optional
            "bugzilla": {
                "product":                  string
            },                                          # optional
            "brew": {
                "default_target":           string,     # optional
                "allowed_tags":             [string]    # optional
            },                                          # optional
            "product_pages": {
                "release_id":               int
            },                                          # optional
            "component_dist_git_branch":    string,     # optional
            "include_inactive":             bool,       # optional
            "include_trees":                [string],   # optional
            "integrated_with:               string      # optional
        }

    The changed attributes must yield a different release_id, therefore
    change in at least one of `short`, `version`, `base_product` or
    `release_type` is required.

    If `component_dist_git_branch` is present, it will be set for all
    release components under the newly created release. If missing, release
    components will be cloned without changes.

    If `include_inactive` is False, the inactive release_components belong to
    the old release won't be cloned to new release.
    Default it will clone all release_components to new release.

    If `include_tree` is specified, it should contain a list of
    Variant.Arch pairs that should be cloned. If not given, all trees will
    be cloned. If the list is empty, no trees will be cloned.
    """

PRODUCT_DOC = {
    'update': """
        %(PUT_OPTIONAL_PARAM_WARNING)s

        __Method__: PUT, PATCH

        __URL__: $LINK:product-detail:short$

        __Data__:

        %(WRITABLE_SERIALIZER)s

        Please note that if you update the `short` field, the URL of this
        product will change. The change of short name is *not* propagated to
        product versions nor releases.

        __Response__:

        %(SERIALIZER)s
        """
}


def extend_docstrings():
    from pdc.apps.release.views import ReleaseViewSet, ReleaseCloneViewSet, ProductViewSet
    for method, doc in RELEASE_DOCS.iteritems():
        getattr(ReleaseViewSet, method).__func__.__doc__ = doc
    ReleaseCloneViewSet.create.__func__.__doc__ = CLONE_DOC
    for method, doc in PRODUCT_DOC.iteritems():
        getattr(ProductViewSet, method).__func__.__doc__ = doc


def extend_product_serializer():
    from pdc.apps.common.constants import PUT_OPTIONAL_PARAM_WARNING
    from pdc.apps.release.views import ProductViewSet
    from rhpdc.apps.rhbindings.serializers import ExtendedProductSerializer
    if hasattr(ExtendedProductSerializer, 'Meta') and hasattr(ExtendedProductSerializer.Meta, 'fields'):
        ExtendedProductSerializer.Meta.fields = ExtendedProductSerializer.Meta.fields + ('internal', )
    ProductViewSet.serializer_class = ExtendedProductSerializer
    writable_serializer_str = """
    {
        "internal (optional, default=false)": "boolean"
        "name": "string",
        "short": "string"
    }
    """
    serializer_str = """
    {
        "active (read-only)": "boolean",
        "internal (optional, default=false)": "boolean",
        "name": "string",
        "product_versions (read-only)": [
            "product_version_id"
        ],
        "short": "string"
    }
    """
    filters = ["* `active` (bool)", "* `internal` (bool)", "* `name` (string)", "* `short` (string)",
               "* `ordering` is used to override the ordering of the results, the value could be: ['short', 'name'] ."]
    filter_str = '\n'.join(filters)
    ProductViewSet.docstring_macros = {'WRITABLE_SERIALIZER': writable_serializer_str,
                                       "SERIALIZER": serializer_str,
                                       "FILTERS": filter_str}
    ProductViewSet.docstring_macros.update(PUT_OPTIONAL_PARAM_WARNING)

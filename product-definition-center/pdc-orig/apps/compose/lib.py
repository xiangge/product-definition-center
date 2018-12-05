# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 Red Hat
# Licensed under The MIT License (MIT)
# http://opensource.org/licenses/MIT
#

import os
import json

import kobo
import productmd
from productmd.rpms import Rpms

from django.db import transaction, connection
from django.db.models import Q
from rest_framework import serializers

from pdc.apps.package.models import RPM
from pdc.apps.common import hacks as common_hacks
from pdc.apps.common import models as common_models
from pdc.apps.package import models as package_models
from pdc.apps.repository import models as repository_models
from pdc.apps.release import models as release_models
from pdc.apps.release import lib
from pdc.apps.compose import models
from pdc.apps.compose.serializers import ComposeTreeSerializer
from pdc.apps.release.models import Release
from pdc.apps.component.models import ReleaseComponent
from pdc.apps.repository.models import ContentCategory


def _maybe_raise_inconsistency_error(composeinfo, manifest, name):
    """Raise ValidationError if compose id is not the same in both files.
    The name should describe the kind of manifest.
    """
    if composeinfo.compose.id != manifest.compose.id:
        raise serializers.ValidationError(
            {'detail': ['Inconsistent data: different compose id in composeinfo and {0} file.'.format(name)]})


def get_or_insert_rpm(rpms_in_db, cursor, rpm_nevra, srpm_nevra, filename):
    rpm_id = rpms_in_db.get(rpm_nevra, None)
    if not rpm_id:
        rpm_id = package_models.RPM.bulk_insert(cursor, rpm_nevra, filename, srpm_nevra)
        rpms_in_db[rpm_nevra] = rpm_id
    return rpm_id


def insert_compose_rpms_if_nonexist(compose_rpms_in_db, cursor,
                                    variant_arch_id, rpm_id,
                                    content_category_id, sigkey_id, path_id):
    key = "%s/%s" % (variant_arch_id, rpm_id)
    if key not in compose_rpms_in_db:
        models.ComposeRPM.bulk_insert(cursor,
                                      variant_arch_id,
                                      rpm_id,
                                      content_category_id,
                                      sigkey_id,
                                      path_id)
        compose_rpms_in_db.add(key)


def _link_compose_to_integrated_product(request, compose, variant):
    """
    If the variant belongs to an integrated layered product, update the compose
    so that it is linked to the release for that product. Note that the variant
    argument should be variant retrieved from compose info, not a PDC model.
    """
    release = variant.release
    if release.name:
        integrated_from_release = lib.get_or_create_integrated_release(
            request,
            compose.release,
            release
        )
        compose.linked_releases.add(integrated_from_release)


def _add_compose_create_msg(request, compose_obj):
    """
    Add compose create message to request._messagings.
    """
    msg = {'action': 'create',
           'compose_id': compose_obj.compose_id,
           'compose_date': compose_obj.compose_date.isoformat(),
           'compose_type': compose_obj.compose_type.name,
           'compose_respin': compose_obj.compose_respin}
    request._request._messagings.append(('.compose', json.dumps(msg)))


def _add_import_msg(request, compose_obj, attribute, count):
    """
    Add import message to request._messagings.

    - `attribute` should be something like 'images' or 'rpms'.
    - `count` should indicate the number of those entities which were imported.
    """
    msg = {'attribute': attribute,
           'count': count,
           'action': 'import',
           'compose_id': compose_obj.compose_id,
           'compose_date': compose_obj.compose_date.isoformat(),
           'compose_type': compose_obj.compose_type.name,
           'compose_respin': compose_obj.compose_respin}
    request._request._messagings.append(('.' + attribute, json.dumps(msg)))


def _store_relative_path_for_compose(compose_obj, variants_info, variant, variant_obj, add_to_changelog):
    vp = productmd.composeinfo.VariantPaths(variant)
    common_hacks.deserialize_wrapper(vp.deserialize, variants_info.get(variant.name, {}).get('paths', {}))
    for path_type in vp._fields:
        path_type_obj, created = models.PathType.objects.get_or_create(name=path_type)
        if created:
            add_to_changelog.append(path_type_obj)
        for arch in variant.arches:
            field_value = getattr(vp, path_type)
            if field_value and field_value.get(arch, None):
                arch_obj = common_models.Arch.objects.get(name=arch)
                crp_obj, created = models.ComposeRelPath.objects.get_or_create(arch=arch_obj, variant=variant_obj,
                                                                               compose=compose_obj, type=path_type_obj,
                                                                               path=field_value[arch])
                if created:
                    add_to_changelog.append(crp_obj)


@transaction.atomic(savepoint=False)
def compose__import_rpms(request, release_id, composeinfo, rpm_manifest):
    release_obj = release_models.Release.objects.get(release_id=release_id)

    ci = productmd.composeinfo.ComposeInfo()
    common_hacks.deserialize_wrapper(ci.deserialize, composeinfo)
    rm = Rpms()
    common_hacks.deserialize_wrapper(rm.deserialize, rpm_manifest)

    _maybe_raise_inconsistency_error(ci, rm, 'rpms')

    compose_date = "%s-%s-%s" % (ci.compose.date[:4], ci.compose.date[4:6], ci.compose.date[6:])
    compose_type = models.ComposeType.objects.get(name=ci.compose.type)
    acceptance_status = models.ComposeAcceptanceTestingState.objects.get(name='untested')
    compose_obj, created = lib._logged_get_or_create(
        request, models.Compose,
        release=release_obj,
        compose_id=ci.compose.id,
        compose_date=compose_date,
        compose_type=compose_type,
        compose_respin=ci.compose.respin,
        compose_label=ci.compose.label or None,
        acceptance_testing=acceptance_status,
    )
    if created and hasattr(request._request, '_messagings'):
        # add message
        _add_compose_create_msg(request, compose_obj)

    rpms_in_db = {}
    qs = package_models.RPM.objects.all()
    for rpm in qs.iterator():
        key = "%s-%s:%s-%s.%s" % (rpm.name, rpm.epoch, rpm.version, rpm.release, rpm.arch)
        rpms_in_db[key] = rpm.id

    cursor = connection.cursor()
    add_to_changelog = []
    imported_rpms = 0
    variants_info = composeinfo['payload']['variants']

    for variant in ci.get_variants(recursive=True):
        _link_compose_to_integrated_product(request, compose_obj, variant)
        variant_type = release_models.VariantType.objects.get(name=variant.type)
        variant_obj, created = models.Variant.objects.get_or_create(
            compose=compose_obj,
            variant_id=variant.id,
            variant_uid=variant.uid,
            variant_name=variant.name,
            variant_type=variant_type
        )
        if created:
            add_to_changelog.append(variant_obj)

        _store_relative_path_for_compose(compose_obj, variants_info, variant, variant_obj, add_to_changelog)

        for arch in variant.arches:
            arch_obj = common_models.Arch.objects.get(name=arch)
            var_arch_obj, _ = models.VariantArch.objects.get_or_create(arch=arch_obj,
                                                                       variant=variant_obj)

            compose_rpms_in_db = set()
            qs = models.ComposeRPM.objects.filter(variant_arch=var_arch_obj).values_list('variant_arch_id',
                                                                                         'rpm_id')
            for (variant_arch_id, rpm_id) in qs.iterator():
                key = "%s/%s" % (variant_arch_id, rpm_id)
                compose_rpms_in_db.add(key)

            sources = set()
            for srpm_nevra, rpms in rm.rpms.get(variant.uid, {}).get(arch, {}).iteritems():
                sources.add(srpm_nevra)
                for rpm_nevra, rpm_data in rpms.iteritems():
                    imported_rpms += 1
                    path, filename = os.path.split(rpm_data['path'])
                    rpm_id = get_or_insert_rpm(rpms_in_db, cursor, rpm_nevra, srpm_nevra, filename)
                    sigkey_id = common_models.SigKey.get_cached_id(rpm_data["sigkey"], create=True)
                    path_id = models.Path.get_cached_id(path, create=True)
                    content_category = rpm_data["category"]
                    content_category_id = repository_models.ContentCategory.get_cached_id(content_category)
                    insert_compose_rpms_if_nonexist(compose_rpms_in_db, cursor,
                                                    var_arch_obj.id, rpm_id,
                                                    content_category_id, sigkey_id, path_id)

    for obj in add_to_changelog:
        lib._maybe_log(request, True, obj)

    request.changeset.add('notice', 0, 'null',
                          json.dumps({
                              'compose': compose_obj.compose_id,
                              'num_linked_rpms': imported_rpms,
                          }))

    if hasattr(request._request, '_messagings'):
        _add_import_msg(request, compose_obj, 'rpms', imported_rpms)

    return compose_obj.compose_id, imported_rpms


@transaction.atomic(savepoint=False)
def compose__import_images(request, release_id, composeinfo, image_manifest):
    release_obj = release_models.Release.objects.get(release_id=release_id)

    ci = productmd.composeinfo.ComposeInfo()
    common_hacks.deserialize_wrapper(ci.deserialize, composeinfo)

    im = productmd.images.Images()
    common_hacks.deserialize_wrapper(im.deserialize, image_manifest)

    _maybe_raise_inconsistency_error(ci, im, 'images')

    compose_date = "%s-%s-%s" % (ci.compose.date[:4], ci.compose.date[4:6], ci.compose.date[6:])
    compose_type = models.ComposeType.objects.get(name=ci.compose.type)
    compose_obj, created = lib._logged_get_or_create(
        request, models.Compose,
        release=release_obj,
        compose_id=ci.compose.id,
        compose_date=compose_date,
        compose_type=compose_type,
        compose_respin=ci.compose.respin,
        compose_label=ci.compose.label or None,
    )
    if created and hasattr(request._request, '_messagings'):
        # add message
        _add_compose_create_msg(request, compose_obj)

    add_to_changelog = []
    imported_images = 0

    variants_info = composeinfo['payload']['variants']
    for variant in ci.get_variants(recursive=True):
        _link_compose_to_integrated_product(request, compose_obj, variant)
        variant_type = release_models.VariantType.objects.get(name=variant.type)
        variant_obj, created = models.Variant.objects.get_or_create(
            compose=compose_obj,
            variant_id=variant.id,
            variant_uid=variant.uid,
            variant_name=variant.name,
            variant_type=variant_type
        )
        if created:
            add_to_changelog.append(variant_obj)

        _store_relative_path_for_compose(compose_obj, variants_info, variant, variant_obj, add_to_changelog)

        for arch in variant.arches:
            arch_obj = common_models.Arch.objects.get(name=arch)
            var_arch_obj, created = models.VariantArch.objects.get_or_create(arch=arch_obj, variant=variant_obj)

            for i in im.images.get(variant.uid, {}).get(arch, []):
                path, file_name = os.path.split(i.path)
                path_id = models.Path.get_cached_id(path, create=True)

                image, _ = package_models.Image.objects.get_or_create(
                    file_name=file_name, sha256=i.checksums["sha256"],
                    defaults={
                        'image_format_id': package_models.ImageFormat.get_cached_id(i.format),
                        'image_type_id': package_models.ImageType.get_cached_id(i.type),
                        'disc_number': i.disc_number,
                        'disc_count': i.disc_count,
                        'arch': i.arch,
                        'mtime': i.mtime,
                        'size': i.size,
                        'bootable': i.bootable,
                        'implant_md5': i.implant_md5,
                        'volume_id': i.volume_id,
                        'md5': i.checksums.get("md5", None),
                        'sha1': i.checksums.get("sha1", None),
                        'subvariant': getattr(i, 'subvariant', None),
                    }
                )

                mi, created = models.ComposeImage.objects.get_or_create(
                    variant_arch=var_arch_obj,
                    image=image,
                    path_id=path_id)
                imported_images += 1

    for obj in add_to_changelog:
        lib._maybe_log(request, True, obj)

    request.changeset.add('notice', 0, 'null',
                          json.dumps({
                              'compose': compose_obj.compose_id,
                              'num_linked_images': imported_images,
                          }))

    if hasattr(request._request, '_messagings'):
        _add_import_msg(request, compose_obj, 'images', imported_images)

    return compose_obj.compose_id, imported_images


def _set_compose_tree_location(request, compose_id, composeinfo, location, url, scheme):
    ci = productmd.composeinfo.ComposeInfo()
    common_hacks.deserialize_wrapper(ci.deserialize, composeinfo)
    num_set_locations = 0
    synced_content = [item.name for item in ContentCategory.objects.all()]

    for variant in ci.get_variants(recursive=True):
        variant_uid = variant.uid
        variant_obj = models.Variant.objects.get(compose__compose_id=compose_id, variant_uid=variant_uid)
        for arch_name in variant.arches:
            data = {'compose': compose_id,
                    'variant': variant_uid,
                    'arch': arch_name,
                    'location': location,
                    'url': url,
                    'scheme': scheme,
                    'synced_content': synced_content}
            request.data['compose'] = compose_id
            try:
                obj = models.ComposeTree.objects.get(compose__compose_id=compose_id, variant=variant_obj,
                                                     arch__name=arch_name, location__short=location)
                # update
                serializer = ComposeTreeSerializer(obj, data=data, many=False, context={'request': request})
            except models.ComposeTree.DoesNotExist:
                # create
                serializer = ComposeTreeSerializer(data=data, many=False, context={'request': request})

            if serializer.is_valid(raise_exception=True):
                serializer.save()
                num_set_locations += 1

    request.changeset.add('notice', 0, 'null',
                          json.dumps({
                              'compose': compose_id,
                              'num_set_locations': num_set_locations,
                          }))
    return num_set_locations


@transaction.atomic(savepoint=False)
def compose__full_import(request, release_id, composeinfo, rpm_manifest, image_manifest, location, url, scheme):
    compose_id, imported_rpms = compose__import_rpms(request, release_id, composeinfo, rpm_manifest)
    # if compose__import_images return successfully, it should return same compose id
    _, imported_images = compose__import_images(request, release_id, composeinfo, image_manifest)
    set_locations = _set_compose_tree_location(request, compose_id, composeinfo, location, url, scheme)
    return compose_id, imported_rpms, imported_images, set_locations


def _find_composes_srpm_name_with_rpm_nvr(nvr):
    """
    Filter composes and SRPM's name with rpm nvr
    """
    try:
        nvr = kobo.rpmlib.parse_nvr(nvr)
    except ValueError:
        raise ValueError("Invalid NVR: %s" % nvr)
    q = Q()
    q &= Q(variant__variantarch__composerpm__rpm__name=nvr["name"])
    q &= Q(variant__variantarch__composerpm__rpm__version=nvr["version"])
    q &= Q(variant__variantarch__composerpm__rpm__release=nvr["release"])

    rpms = RPM.objects.filter(name=nvr["name"], version=nvr["version"], release=nvr["release"])
    srpm_name = None
    if rpms:
        srpm_name = list(set([rpm.srpm_name for rpm in rpms.distinct()]))[0]
    if srpm_name is None:
        raise ValueError("not found")
    return models.Compose.objects.filter(q).distinct(), srpm_name


def find_bugzilla_products_and_components_with_rpm_nvr(nvr):
    """
    Filter bugzilla products and components with rpm nvr
    """
    composes, srpm_name = _find_composes_srpm_name_with_rpm_nvr(nvr)
    release_ids = [compose.release for compose in composes]
    releases = [Release.objects.get(release_id=release_id) for release_id in release_ids]
    result = []
    for release in releases:
        bugzilla = dict()
        bugzilla['bugzilla_product'] = release.bugzilla_product

        component_names = common_hacks.srpm_name_to_component_names(srpm_name)
        release_components = ReleaseComponent.objects.filter(
            release=release,
            name__in=component_names).distinct()
        bugzilla['bugzilla_component'] = [rc.bugzilla_component.export()
                                          for rc in release_components
                                          if rc.bugzilla_component]
        if bugzilla not in result:
            result.append(bugzilla)
    return result

import json

from django.dispatch import receiver
from django.db import models

from pdc.apps.release.models import Product, Release
from pdc.apps.release import signals as release_signals


class ReleaseBrewMapping(models.Model):
    release        = models.OneToOneField(Release, related_name="brew_mapping")
    default_target = models.CharField(max_length=200, blank=True, null=True)

    def export(self):
        return {'release_id': self.release.release_id,
                'default_target': self.default_target,
                'allowed_tags': [x.tag_name for x in self.allowed_tags.all()]}

    def __unicode__(self):
        return 'Brew mapping for %s' % self.release.release_id

    def is_empty(self):
        """Check if the mapping has no default target and no tags."""
        return not (self.default_target or bool(self.allowed_tags.all()))


class BrewTag(models.Model):
    brew_mapping = models.ForeignKey(ReleaseBrewMapping, related_name='allowed_tags')
    tag_name     = models.CharField(max_length=200)

    class Meta:
        unique_together = ('brew_mapping', 'tag_name')

    def __unicode__(self):
        return self.tag_name


def log_change_in_brew_mapping(sender, request, release, **kwargs):
    """
    This handler is executed after a new release is saved or an existing
    release is updated. It looks if there is saved old value for brew mapping
    and creates appropriate changelog entries.
    """
    old_data = getattr(request, '_old_bindings_data', {})
    if hasattr(release, 'brew_mapping'):
        old_val = 'null'
        if 'brew_mapping' in old_data:
            old_val = old_data['brew_mapping'][1]
        pk = release.brew_mapping.pk
        new_val = json.dumps(release.brew_mapping.export())
        if release.brew_mapping.is_empty():
            new_val = 'null'
        request.changeset.add('ReleaseBrewMapping', pk, old_val, new_val)
    elif 'brew_mapping' in old_data:
        old_id, old_val = old_data['brew_mapping']
        request.changeset.add('ReleaseBrewMapping', old_id, old_val, 'null')


class ProductPagesLink(models.Model):
    release             = models.OneToOneField(Release, related_name="product_pages_link")
    product_pages_id    = models.PositiveIntegerField()

    def export(self):
        return {'release_id': self.release.release_id,
                'product_pages_id': self.product_pages_id}

    def __unicode__(self):
        return 'PDC<%s> -> PP<%d>' % (self.release.release_id, self.product_pages_id)


class Errata(models.Model):
    release             = models.OneToOneField(Release)
    product_version    = models.CharField(max_length=200, blank=True, null=True)

    def export(self):
        return {'release_id': self.release.release_id,
                'product_version': self.product_version}

    def __unicode__(self):
        return 'PDC<%s> -> PV<%d>' % (self.release.release_id, self.product_version)


class InternalProudct(models.Model):
    product = models.OneToOneField(Product, related_name="internal", primary_key=True)

    def export(self):
        return {'product': self.product.short,
                'internal': True}

    def __unicode__(self):
        return 'Product<%s> -> Internal<True>' % self.product.short


def _member_log_cloned(sender, request, release, member_name, member_log_name, **kwargs):
    if hasattr(release, member_name):
        request.changeset.add(member_log_name,
                              getattr(release, member_name).pk,
                              'null',
                              json.dumps(getattr(release, member_name).export()))


@receiver(release_signals.release_clone)
def _log_cloned(sender, request, release, **kwargs):
    for member_name, member_log_name in (('errata', 'errataproductversion'),
                                         ('product_pages_link', 'productpageslink'),
                                         ('brew_mapping', 'ReleaseBrewMapping')):
        _member_log_cloned(sender, request, release, member_name, member_log_name, **kwargs)


def _common_release_log_change(sender, request, release, member_name, member_log_name, **kwargs):
    old_data = getattr(request, '_old_bindings_data', {})
    if hasattr(release, member_name):
        old_val = 'null'
        if member_name in old_data:
            old_val = old_data[member_name][1]
        request.changeset.add(member_log_name,
                              getattr(release, member_name).pk,
                              old_val,
                              json.dumps(getattr(release, member_name).export()))
    elif member_name in old_data:
        old_id, old_val = old_data[member_name]
        request.changeset.add(member_log_name, old_id, old_val, 'null')


@receiver(release_signals.release_post_update)
def log_changes_for_release(sender, request, release, **kwargs):
    """
    This handler is executed after a new release is saved or an existing
    release is updated. It looks if there is saved old value for
    errata/product pages link/brew mapping and creates appropriate changelog entries.
    """
    _common_release_log_change(sender, request, release, 'errata', 'errataproductversion', **kwargs)
    _common_release_log_change(sender, request, release, 'product_pages_link', 'productpageslink', **kwargs)
    log_change_in_brew_mapping(sender, request, release, **kwargs)


def _store_original_value(sender, request, release, member_name, **kwargs):
    if not hasattr(request, '_old_bindings_data'):
        request._old_bindings_data = {}
    if hasattr(release, member_name):
        request._old_bindings_data[member_name] = (
            getattr(release, member_name).pk,
            json.dumps(getattr(release, member_name).export())
        )


@receiver(release_signals.release_pre_update)
def store_release_original_values(sender, request, release, **kwargs):
    """
    This handler is executed before an existing release is updated. It stores
    the old values for errata/product pages link/brew mapping in the request.
    """
    for member_name in ('errata', 'product_pages_link', 'brew_mapping'):
        _store_original_value(sender, request, release, member_name, **kwargs)


INTERNAL_FLAG_STRING = 'internal'


@receiver(release_signals.product_post_update)
def log_changes_for_product(sender, request, product, **kwargs):
    """
    This handler is executed after a new product is saved or an existing
    product is updated. It looks if there is saved old value for
    internal flag status and creates appropriate changelog entries.
    """
    old_data = getattr(request, '_old_bindings_data', {})
    if hasattr(product, INTERNAL_FLAG_STRING):
        old_val = 'null' if INTERNAL_FLAG_STRING not in old_data else old_data[INTERNAL_FLAG_STRING]
        try:
            product.internal.refresh_from_db()
        except InternalProudct.DoesNotExist:
            new_val = False
        else:
            new_val = True
        if old_val != new_val:
            request.changeset.add(INTERNAL_FLAG_STRING,
                                  product.pk,
                                  old_val,
                                  new_val)
    elif INTERNAL_FLAG_STRING in old_data:
        old_val = old_data[INTERNAL_FLAG_STRING]
        if old_val:
            request.changeset.add(INTERNAL_FLAG_STRING, product.pk, old_val, False)
    elif not old_data:
        # create with internal flag is false
        request.changeset.add(INTERNAL_FLAG_STRING, product.pk, 'null', False)


@receiver(release_signals.product_pre_update)
def store_product_original_values(sender, request, product, **kwargs):
    """
    This handler is executed before an existing product is updated. It stores
    the old values for internal flag status in the request.
    """
    if not hasattr(request, '_old_bindings_data'):
        request._old_bindings_data = {}
    if hasattr(product, INTERNAL_FLAG_STRING):
        request._old_bindings_data[INTERNAL_FLAG_STRING] = True if product.internal else False
    else:
        request._old_bindings_data[INTERNAL_FLAG_STRING] = False

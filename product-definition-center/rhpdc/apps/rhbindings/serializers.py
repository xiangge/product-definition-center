# NOTE it is important not to import any serializers module from other apps.
# Doing that could cause cyclic imports and break the application.
from django.core.exceptions import ValidationError
from django.dispatch import receiver

from rest_framework import serializers

from pdc.apps.common.serializers import StrictSerializerMixin
from . import models
from pdc.apps.release import signals as release_signals
from pdc.apps.release.serializers import ProductSerializer


class BrewTagSerializer(serializers.BaseSerializer):
    doc_format = 'string'

    def to_representation(self, obj):
        return obj.tag_name

    def to_internal_value(self, data, files=None):
        if not isinstance(data, basestring):
            raise serializers.ValidationError('Invalid tag name "%s". Must be a string.' % data)
        return data


class ReleaseBrewMappingNestedSerializer(StrictSerializerMixin, serializers.ModelSerializer):
    allowed_tags    = BrewTagSerializer(required=False, many=True)
    default_target  = serializers.CharField(required=False, allow_null=True)

    key_combination_error = 'add_allowed_tags/remove_allowed_tags can not be combined with allowed_tags.'
    add_del_put_error = 'add_allowed_tags/remove_allowed_tags can only be used in partial update.'

    extra_fields = ('add_allowed_tags', 'remove_allowed_tags')

    class Meta:
        model = models.ReleaseBrewMapping
        fields = ('default_target', 'allowed_tags')

    def to_representation(self, mapping):
        if mapping.is_empty():
            return None
        return super(ReleaseBrewMappingNestedSerializer, self).to_representation(mapping)


class ProductPagesLinkSerializer(StrictSerializerMixin, serializers.ModelSerializer):
    release_id = serializers.IntegerField(source='product_pages_id')
    extra_fields = ('add_allowed_tags', 'remove_allowed_tags')

    class Meta:
        model = models.ProductPagesLink
        fields = ('release_id', )


class ErrataSerializer(StrictSerializerMixin, serializers.ModelSerializer):

    class Meta:
        model = models.Errata
        fields = ('product_version', )


class InternalProductSerializer(serializers.BooleanField):

    def to_representation(self, obj):
        result = False
        if obj:
            try:
                obj.refresh_from_db()
            except models.InternalProudct.DoesNotExist:
                pass
            else:
                result = True
        return result


@receiver(release_signals.release_serializer_extract_data)
def product_pages_extract_data(sender, validated_data, **kwargs):
    sender.product_pages_data = validated_data.pop('product_pages_link', None)


@receiver(release_signals.release_serializer_post_create)
def product_pages_post_create(sender, release, **kwargs):
    if sender.product_pages_data:
        models.ProductPagesLink.objects.create(release=release, **sender.product_pages_data)


@receiver(release_signals.release_serializer_post_update)
def product_pages_post_update(sender, release, **kwargs):
    if not hasattr(release, 'product_pages_link'):
        product_pages_post_create(sender, release)
        return

    explicit_remove = 'product_pages' in sender.initial_data and sender.product_pages_data is None
    implicit_remove = not sender.partial and not sender.product_pages_data
    if explicit_remove or implicit_remove:
        release.product_pages_link.delete()
    elif 'product_pages_id' in (sender.product_pages_data or {}):
        release.product_pages_link.product_pages_id = sender.product_pages_data['product_pages_id']
        release.product_pages_link.save()


@receiver(release_signals.release_serializer_extract_data)
def errata_extract_data(sender, validated_data, **kwargs):
    sender.errata = validated_data.pop('errata', None)


@receiver(release_signals.release_serializer_post_create)
def errata_post_create(sender, release, **kwargs):
    if sender.errata:
        models.Errata.objects.create(release=release, **sender.errata)


@receiver(release_signals.release_serializer_post_update)
def errata_post_update(sender, release, **kwargs):
    if not hasattr(release, 'errata'):
        errata_post_create(sender, release)
        return

    explicit_remove = 'errata' in sender.initial_data and sender.errata is None
    implicit_remove = not sender.partial and not sender.errata
    if explicit_remove or implicit_remove:
        release.errata.delete()
    elif 'product_version' in (sender.errata or {}):
        release.errata.product_version = sender.errata['product_version']
        release.errata.save()


@receiver(release_signals.release_serializer_extract_data)
def brew_extract_data(sender, validated_data, **kwargs):
    sender.release_brew_data = validated_data.pop('brew_mapping', None)
    initial = sender.initial_data.get('brew') or {}
    if not sender.partial and ('add_allowed_tags' in initial or 'remove_allowed_tags' in initial):
        raise ValidationError(ReleaseBrewMappingNestedSerializer.add_del_put_error)


def _get_brew_add_and_del_allowed_tags(data):
    brew_value = data.get('brew') if data.get('brew') else {}
    add_allowed_tags = brew_value.get('add_allowed_tags', [])
    del_allowed_tags = brew_value.get('remove_allowed_tags', [])
    return add_allowed_tags, del_allowed_tags


@receiver(release_signals.release_serializer_post_create)
def brew_post_create(sender, release, **kwargs):
    add_allowed_tags, del_allowed_tags = _get_brew_add_and_del_allowed_tags(sender.initial_data)
    if sender.release_brew_data or add_allowed_tags:
        data = sender.release_brew_data
        if (add_allowed_tags or del_allowed_tags) and 'allowed_tags' in data:
            raise ValidationError(ReleaseBrewMappingNestedSerializer.key_combination_error)
        if del_allowed_tags:
            raise ValidationError('Can not remove non-existing tag')
        allowed_tags = data.pop('allowed_tags', []) + add_allowed_tags
        mapping = models.ReleaseBrewMapping.objects.create(release=release, **data)
        for allowed_tag in allowed_tags:
            mapping.allowed_tags.create(tag_name=allowed_tag)


@receiver(release_signals.release_serializer_post_update)
def brew_post_update(sender, release, **kwargs):
    if not hasattr(release, 'brew_mapping'):
        brew_post_create(sender, release)
        return
    mapping = release.brew_mapping

    explicit_remove = 'brew' in sender.initial_data and sender.release_brew_data is None
    implicit_remove = not sender.partial and not sender.release_brew_data
    if explicit_remove or implicit_remove:
        mapping.delete()
        return

    add_allowed_tags, del_allowed_tags = _get_brew_add_and_del_allowed_tags(sender.initial_data)
    if sender.release_brew_data or add_allowed_tags or del_allowed_tags:
        data = sender.release_brew_data
        mapping.default_target = data.get('default_target', mapping.default_target if sender.partial else None)

        if (add_allowed_tags or del_allowed_tags) and 'allowed_tags' in data:
            raise ValidationError(ReleaseBrewMappingNestedSerializer.key_combination_error)
        for tag in add_allowed_tags:
            mapping.allowed_tags.create(tag_name=tag)
        if del_allowed_tags:
            tags = mapping.allowed_tags.filter(tag_name__in=del_allowed_tags)
            if not tags:
                raise ValidationError('Can not remove non-existing tag')
            tags.delete()
        if 'allowed_tags' in data:
            mapping.allowed_tags.all().delete()
            for tag in data['allowed_tags']:
                mapping.allowed_tags.create(tag_name=tag)

        mapping.save()


class ExtendedProductSerializer(ProductSerializer):
    internal = InternalProductSerializer(required=False, read_only=False, default=False)

    def save(self, **kwargs):
        internal_flag_value = self.validated_data.pop('internal', None)
        instance = super(ExtendedProductSerializer, self).save(**kwargs)
        if internal_flag_value is not None:
            if not hasattr(instance, 'internal') and internal_flag_value:
                models.InternalProudct.objects.create(product=instance)
            elif hasattr(instance, 'internal') and not internal_flag_value:
                instance.internal.delete()
        return instance

    def to_representation(self, value):
        data = super(ExtendedProductSerializer, self).to_representation(value)
        if 'internal' in data and data['internal'] is None:
            data['internal'] = False
        return data


def add_field(serializer, field_name, field):
    """Add field to a serializer."""
    serializer._declared_fields[field_name] = field
    if hasattr(serializer, 'Meta') and hasattr(serializer.Meta, 'fields'):
        serializer.Meta.fields = serializer.Meta.fields + (field_name, )


def extend_release_serializer(release_serializer):
    add_field(release_serializer,
              'brew',
              ReleaseBrewMappingNestedSerializer(source='brew_mapping',
                                                 required=False,
                                                 allow_null=True))
    add_field(release_serializer,
              'product_pages',
              ProductPagesLinkSerializer(source='product_pages_link',
                                         required=False,
                                         allow_null=True))
    add_field(release_serializer,
              'errata',
              ErrataSerializer(required=False, allow_null=True))


def extend_product_serializer(product_serializer):
    if hasattr(product_serializer, 'Meta') and hasattr(product_serializer.Meta, 'fields'):
        product_serializer.Meta.fields = product_serializer.Meta.fields + ('internal', )

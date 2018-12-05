from django.apps import AppConfig


class BindingsConfig(AppConfig):
    name = 'rhpdc.apps.rhbindings'
    label = 'rhbindings'
    verbose_name = 'Bindings for various models'

    def ready(self):
        self._extend_filters()
        self._extend_serializers()

        self._connect_signals()

    def _connect_signals(self):
        from pdc.apps.utils.utils import connect_app_models_pre_save_signal
        models_name = ('ReleaseBrewMapping', 'BrewTag')
        connect_app_models_pre_save_signal(self, [self.get_model(model_name) for model_name in models_name])

    def _extend_filters(self):
        from . import filters
        from pdc.apps.release import filters as release_filters
        filters.extend_release_filter(release_filters.ReleaseFilter)
        filters.extend_product_filter(release_filters.ProductFilter)

    def _extend_serializers(self):
        from . import serializers
        from pdc.apps.release import serializers as release_serializers
        serializers.extend_release_serializer(release_serializers.ReleaseSerializer)

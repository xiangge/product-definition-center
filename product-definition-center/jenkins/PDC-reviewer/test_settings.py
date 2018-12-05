"""
Extra Django settings for test environment of pdc project.
"""

import os.path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.sqlite3',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# disable PERMISSION while testing
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'pdc.apps.auth.authentication.TokenAuthenticationWithChangeSet',
        'rest_framework.authentication.SessionAuthentication',
    ),

#    'DEFAULT_PERMISSION_CLASSES': [
#        'rest_framework.permissions.DjangoModelPermissions'
#    ],

    'DEFAULT_FILTER_BACKENDS': ('rest_framework.filters.DjangoFilterBackend',),

    'PAGINATE_BY': 20,

    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'pdc.apps.common.renderers.ReadOnlyBrowsableAPIRenderer',
    ),

    'EXCEPTION_HANDLER': 'pdc.apps.common.handlers.exception_handler'
}

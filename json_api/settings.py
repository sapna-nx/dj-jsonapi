'''
Settings for dj-jsonapi are all namespaced in the DJANGO_JSON_API setting.

    Note:
    This module is an extension of REST framework's settings module and
    provides the same API. More information can be found by referring to
    REST framework's documentation.


To configure JSON-API, you might configure you project's `settings.py` file
to look like this:

DJANGO_JSON_API = {
    'PAGE_SIZE': 20
}

'''
import warnings
from django.conf import settings
from rest_framework import settings as drf_settings

# warn user about conflicting/overwritten REST framework settings.
if hasattr(settings, 'REST_FRAMEWORK') and \
   hasattr(settings, 'DJANGO_JSON_API'):
    warnings.warn(
        "Found `REST_FRAMEWORK` and `DJANGO_JSON_API` in project settings. "
        "REST framework settings are overwritten and have no effect - "
        "the `REST_FRAMEWORK` setting should be removed.",
        stacklevel=1
    )

USER_SETTINGS = getattr(settings, 'DJANGO_JSON_API', None)

# try falling back to REST framework settings. A warning isn't really
# necessary, so long as there is no API settings conflict.
if USER_SETTINGS is None:
    USER_SETTINGS = getattr(settings, 'REST_FRAMEWORK', None)


DEFAULTS = drf_settings.DEFAULTS.copy()
DEFAULTS.update({
    'DEFAULT_RENDERER_CLASSES': (
        'json_api.renderers.APIRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'json_api.parsers.APIParser',
        'json_api.parsers.FormParser',
        'json_api.parsers.MultiPartParser',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.SearchFilter',
        'json_api.filters.RelatedOrderingFilter',
    ),
    'ORDERING_PARAM': 'sort',
    'DEFAULT_PAGINATION_CLASS': 'json_api.pagination.PageNumberPagination',
    # 'DEFAULT_CONTENT_NEGOTIATION_CLASS': 'json_api.negotiation.Negotiator',
    # 'DEFAULT_METADATA_CLASS': 'json_api.metadata.APIMetadata',
    'EXCEPTION_HANDLER': 'json_api.exceptions.handler',
    'FORM_OVERRIDE_DO_PARSE': True,
})

# JSON-API settings
DEFAULTS.update({
    'PATH_DELIMITER': '.',
})


IMPORT_STRINGS = drf_settings.IMPORT_STRINGS


api_settings = drf_settings.APISettings(USER_SETTINGS, DEFAULTS, IMPORT_STRINGS)
drf_settings.api_settings = api_settings


DEFAULT_SETTINGS = {
    'DEFAULT_RENDERER_CLASSES': (
        'json_api.renderers.APIRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'json_api.parsers.JSONParser',
        'json_api.parsers.FormParser',
        'json_api.parsers.MultiPartParser'
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.OrderingFilter',
        'rest_framework.filters.SearchFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'json_api.pagination.PageNumberPagination',
    'DEFAULT_CONTENT_NEGOTIATION_CLASS': 'json_api.negotiation.Negotiator',
}


from collections import OrderedDict
from rest_framework import renderers


class APIRenderer(renderers.JSONRenderer):
    """
    Renderer which serializes to JSON, following the json-api spec.
    """

    media_type = 'application/vnd.api+json'

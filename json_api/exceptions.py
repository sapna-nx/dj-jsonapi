
from rest_framework.exceptions import *
from rest_framework.views import exception_handler as _exception_handler
from rest_framework import status
from django.utils.encoding import force_text


def handler(exc, context):
    return _exception_handler(exc, context)


class APIError(Exception):
    """
    Base class for JSON-API errors.

    Reference:
    http://jsonapi.org/format/#error-objects
    """
    pass


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, detail):
        self.detail = force_text(detail)

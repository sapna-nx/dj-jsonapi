
import sys
from collections import OrderedDict
from rest_framework import exceptions
from rest_framework.views import exception_handler as _exception_handler
from rest_framework import status
from django.core.exceptions import PermissionDenied as DjPermissionDenied
from django.http import Http404
from django.utils.encoding import force_text


def handler(exc, context):
    if isinstance(exc, Http404):
        exc = NotFound()
    elif isinstance(exc, DjPermissionDenied):
        exc = PermissionDenied()

    if not isinstance(exc, APIError) and isinstance(exc, exceptions.APIException):
        module = sys.modules[__name__]
        name = exc.__class__.__name__

        try:
            exc = getattr(module, name)()
        except:
            pass

    return _exception_handler(exc, context)


class APIError(exceptions.APIException):
    """
    Base class for JSON-API errors.

    Reference:
    http://jsonapi.org/format/#error-objects
    """

    def __init__(self, *args, **kwargs):

        error = OrderedDict([
            ('id',      kwargs.pop('id', None)),
            ('links',   kwargs.pop('links', None)),
            ('status',  kwargs.pop('status', None) or self.status_code),
            ('code',    kwargs.pop('code', None)),
            ('title',   kwargs.pop('title', None)),
            ('detail',  None),
            ('source',  kwargs.pop('source', None)),
            ('meta',    kwargs.pop('meta', None)),
        ])

        super(APIError, self).__init__(*args, **kwargs)

        error['detail'] = self.detail

        for key, value in error.items():
            if value is None:
                del error[key]

        self.data = error


class ValidationError(APIError, exceptions.ValidationError):
    pass


class ParseError(APIError, exceptions.ParseError):
    pass


class AuthenticationFailed(APIError, exceptions.AuthenticationFailed):
    pass


class NotAuthenticated(APIError, exceptions.NotAuthenticated):
    pass


class PermissionDenied(APIError, exceptions.PermissionDenied):
    pass


class NotFound(APIError, exceptions.NotFound):
    pass


class MethodNotAllowed(APIError, exceptions.MethodNotAllowed):
    pass


class NotAcceptable(APIError, exceptions.NotAcceptable):
    pass


class Conflict(APIError):
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, detail):
        self.detail = force_text(detail)


class UnsupportedMediaType(APIError, exceptions.UnsupportedMediaType):
    pass


class Throttled(APIError, exceptions.Throttled):
    pass

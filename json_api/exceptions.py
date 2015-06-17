
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
        err_id = kwargs.pop('id', None)
        links = kwargs.pop('links', None)
        status = kwargs.pop('status', None)
        code = kwargs.pop('code', None)
        title = kwargs.pop('title', None)
        source = kwargs.pop('source', None)
        meta = kwargs.pop('meta', None)

        super(APIError, self).__init__(*args, **kwargs)

        detail = self.detail
        status = status or self.status_code

        error = OrderedDict()
        if err_id is not None:
            error['id'] = err_id
        if links is not None:
            error['links'] = links
        if status is not None:
            error['status'] = status
        if code is not None:
            error['code'] = code
        if title is not None:
            error['title'] = title
        if detail is not None:
            error['detail'] = detail
        if source is not None:
            error['source'] = source
        if meta is not None:
            error['meta'] = meta

        self.detail = error



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

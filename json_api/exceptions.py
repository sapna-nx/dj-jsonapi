
from collections import OrderedDict
from rest_framework import exceptions
from rest_framework.views import exception_handler as _exception_handler
from rest_framework import status
from django.core.exceptions import PermissionDenied as DjPermissionDenied
from django.http import Http404
from django.utils.encoding import force_text
from django.utils import six


def handler(exc, context):

    if isinstance(exc, Http404):
        exc = NotFound()

    elif isinstance(exc, DjPermissionDenied):
        exc = PermissionDenied()

    response = _exception_handler(exc, context)

    if response is not None:
        response.data = {'errors': format_error_data(exc)}

    return response


def format_error_data(exc):
    """
    Returns a list of JSON-API error objects from a given exception.
    """
    errors = []

    if isinstance(exc, APIError):
        errors.append(exc.data)

    elif isinstance(exc, ErrorList):
        for error in exc.errors:
            errors += format_error_data(error)

    elif isinstance(exc, exceptions.APIException):
        if isinstance(exc, exceptions.ValidationError):
            errors += [error.data for error in expand_validation_error(exc, exc.detail)]

        else:
            errors.append(APIError(status=exc.status_code, detail=exc.detail).data)

    return errors


def expand_validation_error(base_exc, detail, pointer='/data'):
    errors = []

    if isinstance(detail, list):
        for index, sub_detail in enumerate(detail):

            # base case is a list of validation error strings for a field pointer
            if isinstance(sub_detail, six.string_types):
                errors.append(ValidationError(
                    detail=sub_detail,
                    source={'pointer': pointer}
                ))

            # list of nested error arrays or objects
            else:
                errors += expand_validation_error(base_exc, sub_detail, "%s/%s" % (pointer, index))

    elif isinstance(detail, dict):
        for key, sub_detail in detail.items():
            if key == 'non_field_errors':
                # non attribute errors belong to the overall 'data'.
                errors += expand_validation_error(base_exc, sub_detail, pointer)

            # TODO: determine if there is a more elegant way to handle identity vs attributes
            elif key in ('id', 'type'):
                errors += expand_validation_error(base_exc, sub_detail, "%s/%s" % (pointer, key))

            else:
                errors += expand_validation_error(base_exc, sub_detail, "%s/attributes/%s" % (pointer, key))

    else:
        # TODO: Delete me after testing
        raise Exception("dis is dun broke.")

    return errors


class APIError(exceptions.APIException):
    """
    Base class for JSON-API errors.

    Reference:
    http://jsonapi.org/format/#error-objects
    """

    def __init__(self, *args, **kwargs):

        self._data = OrderedDict([
            ('id',      kwargs.pop('id', None)),
            ('links',   kwargs.pop('links', None)),
            ('status',  kwargs.pop('status', self.status_code)),
            ('code',    kwargs.pop('code', None)),
            ('title',   kwargs.pop('title', None)),
            ('detail',  None),
            ('source',  kwargs.pop('source', None)),
            ('meta',    kwargs.pop('meta', None)),
        ])

        super(APIError, self).__init__(*args, **kwargs)

    @property
    def data(self):
        error = self._data.copy()
        error['detail'] = self.detail

        # filter out empty values
        return OrderedDict((k, v) for k, v in error.items() if v)


class _Conflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, detail):
        self.detail = force_text(detail)


class ValidationError(APIError, exceptions.ValidationError):
    def __init__(self, *args, **kwargs):
        # pull error message back out of the array.
        super(ValidationError, self).__init__(*args, **kwargs)

        # TODO: Figure out a better solution
        if isinstance(self.detail, list) and len(self.detail) == 1:
            self.detail = self.detail[0]


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


class Conflict(APIError, _Conflict):
    pass


class UnsupportedMediaType(APIError, exceptions.UnsupportedMediaType):
    pass


class Throttled(APIError, exceptions.Throttled):
    pass


class ErrorList(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, errors):

        if errors:
            status_codes = [error.status_code for error in errors]
            self.status_code = max(status_codes) // 100 * 100

        self.errors = errors
        self.detail = None

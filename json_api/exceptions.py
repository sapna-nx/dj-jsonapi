
from rest_framework import exceptions, status
from django.utils.encoding import force_text


class Conflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, detail):
        self.detail = force_text(detail)

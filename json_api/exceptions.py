
from rest_framework import exceptions, status


class CONFLICT(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, detail):
        self.detail = force_text(detail)

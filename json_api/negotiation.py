
from rest_framework.negotiation import DefaultContentNegotiation
from json_api.parsers import APIParser
from json_api.renderers import APIRenderer


class APINegotiation(DefaultContentNegotiation):

    def select_parser(self, request, parsers):
        parser = super(APINegotiation, self).select_parser(request, parsers)

        # Servers MUST respond with a 415 Unsupported Media Type status code if
        # a request specifies the header Content-Type: application/vnd.api+json
        # with any media type parameters.
        if isinstance(parser, APIParser):

            # This check needs to be done because some browsers append charset
            # information automatically to the Content-Type header
            content_types = [ct.strip() for ct in request.content_type.split(';')]
            if parser.media_type not in content_types:
                return None

        return parser

    def select_renderer(self, request, renderers, format_suffix=None):
        # Servers MUST respond with a 406 Not Acceptable status code if a
        # request's Accept header contains the JSON API media type and all
        # instances of that media type are modified with media type parameters.
        accepts = self.get_accept_list(request)

        if any(a.startswith(APIRenderer.media_type) for a in accepts):
            if APIRenderer.media_type not in accepts:
                from json_api import exceptions
                raise exceptions.NotAcceptable()

        return super(APINegotiation, self).select_renderer(request, renderers, format_suffix)

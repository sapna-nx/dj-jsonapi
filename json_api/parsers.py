
from rest_framework import parsers


class APIParser(parsers.JSONParser):

    media_type = 'application/vnd.api+json'


class FormParser(parsers.FormParser):
    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses and formats form data to conform to JSON-API resource objects.
        Form data only describes the attributes of a resource object, so the
        parser contstructs the remainder of the resource.

        Note that the QueryDict is flattened into a plain dictionary.
        """
        request = parser_context['request']
        view = parser_context['view']
        data = super(FormParser, self).parse(stream, media_type, parser_context)

        overrides = {}
        for param in [
            'csrfmiddlewaretoken', request._METHOD_PARAM,
            request._CONTENT_PARAM, request._CONTENTTYPE_PARAM,
        ]:
            value = data.pop(param, [None])[0]
            if value:
                overrides[param] = value

        data = {
            'data': {
                'type': view.get_resource_type(),
                'attributes': data.dict(),
            }
        }

        data.update(overrides)

        try:
            lookup_url_kwarg = view.lookup_url_kwarg or view.lookup_field
            # TODO: type conversion shouldn't be hardcoded here.
            data['data']['id'] = int(view.kwargs[lookup_url_kwarg])
        except KeyError:
            pass

        return data


class MultiPartParser(parsers.MultiPartParser):
    """
    Parser for multipart form data, which may include file data.
    """
    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as a multipart encoded form,
        and returns a DataAndFiles object.
        `.data` will be a `QueryDict` containing all the form parameters.
        `.files` will be a `QueryDict` containing all the form files.
        """
        request = parser_context['request']
        view = parser_context['view']
        data_and_files = super(MultiPartParser, self).parse(stream, media_type, parser_context)
        data = data_and_files.data

        overrides = {}
        for param in [
            'csrfmiddlewaretoken', request._METHOD_PARAM,
            request._CONTENT_PARAM, request._CONTENTTYPE_PARAM,
        ]:
            value = data.pop(param, [None])[0]
            if value:
                overrides[param] = value

        data = {
            'data': {
                'type': view.get_resource_type(),
                'attributes': data.dict(),
            }
        }

        data.update(overrides)

        try:
            lookup_url_kwarg = view.lookup_url_kwarg or view.lookup_field
            # TODO: type conversion shouldn't be hardcoded here.
            data['data']['id'] = int(view.kwargs[lookup_url_kwarg])
        except KeyError:
            pass

        data_and_files.data = data
        return data_and_files

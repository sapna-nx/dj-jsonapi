
from rest_framework import parsers


class APIParser(parsers.JSONParser):
    pass


class FormParser(parsers.FormParser):
    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses and formats form data to conform to JSON-API resource objects.
        Form data only describes the attributes of a resource object, so the
        parser contstructs the remainder of the resource.

        Note that the QueryDict is flattened into a plain dictionary.
        """
        view = parser_context['view']
        data = super(FormParser, self).parse(stream, media_type, parser_context)

        data = {
            'data': {
                'type': view.get_resource_type(),
                'attributes': data.dict(),
            }
        }

        try:
            lookup_url_kwarg = view.lookup_url_kwarg or view.lookup_field
            data['data']['id'] = view.kwargs[lookup_url_kwarg]
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
        view = parser_context['view']
        data_and_files = super(MultiPartParser, self).parse(stream, media_type, parser_context)
        data = data_and_files.data

        data = {
            'data': {
                'type': view.get_resource_type(),
                'attributes': data.dict(),
            }
        }

        try:
            lookup_url_kwarg = view.lookup_url_kwarg or view.lookup_field
            data['data']['id'] = view.kwargs[lookup_url_kwarg]
        except KeyError:
            pass

        data_and_files.data = data
        return data_and_files

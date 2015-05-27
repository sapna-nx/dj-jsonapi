
from collections import OrderedDict
from rest_framework import renderers


class APIRenderer(renderers.JSONRenderer):
    """
    Renderer which serializes to JSON, following the json-api spec
    """

    media_type = 'application/json'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        view = renderer_context['view']

        data = OrderedDict((
            ('links', view.get_top_links()),
            ('data', data),
        ))

        return super(APIRenderer, self).render(data, accepted_media_type, renderer_context)

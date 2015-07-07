
from collections import OrderedDict
from django.utils.functional import cached_property
from rest_framework.views import APIView
from json_api.utils.reverse import reverse
from json_api import routers, exceptions


class ResourceView(APIView):
    """
    Base class for all json-api views. Contains some base machinery necessary
    for resolving realtionships and building json-api compliant responses.
    """
    relationships = None
    relname_url_kwarg = 'relname'

    allow_client_generated_ids = False

    # This is somewhat gross, however it does allow us to declaratively set the
    # relationships on the class while still accessing the resolved rels on
    # the instance.
    # The rels cannot be resolved in __init__, as this could potentially set
    # off infinite recursion of relationship resolving.
    # The rels should not be resolved in `initial()`, since this ties resolving
    # to request dispatching.
    def __getattribute__(self, name):
        if name == 'relationships':
            return self._resolved_relationships
        return super(ResourceView, self).__getattribute__(name)

    @cached_property
    def _resolved_relationships(self):
        return self.resolve_relationships(self.__class__.relationships)

    def resolve_relationships(self, relationships):
        """
        Hook for preprocessing/resolving relationship data. This method should
        be overridden if the base relationship descriptor needs to be modified
        with additional data.
        """
        return relationships

    def get_basename(self):
        """
        The `basename` to use for reversing URLs. You may need to override
        this if you provide a base_name to your router.
        """
        # TODO: make less meh?
        self.__router = getattr(self, '__router', routers.BaseAPIRouter())
        return self.__router.get_default_base_name(self)

    def get_default_links(self):
        """
        The default top-level links for the current request. Contains the
        `self` link for the current request.
        This method should be overridden in order to provide addtitional
        top-level default links, such as pagination.
        """
        return OrderedDict([
            ('self', self.request.build_absolute_uri()),
        ])

    def _get_dynamic_views(self):
        detail_views = []
        list_views = []
        for methodname in dir(self.__class__):
            attr = getattr(self.__class__, methodname)
            kwargs = getattr(attr, 'kwargs', None)
            httpmethods = getattr(attr, 'bind_to_methods', None)
            detail = getattr(attr, 'detail', True)
            if httpmethods:
                url_path = kwargs.get('url_path', None) or methodname
                if detail:
                    detail_views.append(url_path.replace('_', '-'))
                else:
                    list_views.append(url_path.replace('_', '-'))

        return detail_views, list_views

    def get_resource_actions(self, resource_id):
        """
        Returns a dictionary of {urlname: url} for a resource's action routes.
        These routes are dynamically generated using the @detail_route
        decorator on view methods.
        """
        base_name = self.get_basename()
        view_names = self._get_dynamic_views()[0]

        return OrderedDict(((
            view_name, reverse("%s-%s" % (base_name, view_name), self.request, args=[resource_id])
        ) for view_name in view_names))

    def get_collection_actions(self):
        """
        Returns a dictionary of {urlname: url} for a collection's action
        routes. These routes are dynamically generated using the @list_route
        decorator on view methods.
        """
        base_name = self.get_basename()
        view_names = self._get_dynamic_views()[1]

        return OrderedDict(((
            view_name, reverse("%s-%s" % (base_name, view_name), self.request)
        ) for view_name in view_names))

    def build_response_body(self, **kwargs):
        """
        Format the top-level repsonse body.
        """
        body = OrderedDict()

        # TODO: One of the following keys is required. There should
        # probably be an internal API error that's raised.
        # if not any(key in kwargs for key in ('data', 'errors', 'meta')):
        #     raise APIErrorOrSomething() or ImproperlyConfigured()

        for key in ('jsonapi', 'links', 'data', 'included', 'errors', 'meta'):
            if key in kwargs:
                body[key] = kwargs[key]
        return body

    def get_relationship(self, relname=None):
        """
        Returns the relationship for a given relationship name. If no name is
        specified, it attempts to get the relationship for the current request.
        """
        if relname is None:
            assert self.relname_url_kwarg in self.kwargs, (
                'Expected view %s to be called with a URL keyword argument '
                'named "%s". Fix your URL conf, or set the '
                '`.relname_url_kwarg` attribute on the view correctly.' %
                (self.__class__.__name__, self.relname_url_kwarg)
            )
            relname = self.kwargs[self.relname_url_kwarg]

        for rel in self.relationships:
            if relname == rel.relname:
                return rel

        # raise 404 if no relationship was found. This also covers calls on
        # '/relationships/'
        raise exceptions.NotFound()

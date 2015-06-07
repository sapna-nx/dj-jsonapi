
from collections import OrderedDict
from rest_framework import routers, views
from rest_framework.response import Response
from django.conf.urls import url
from django.core.urlresolvers import NoReverseMatch
from .utils.reverse import reverse


class BaseAPIRouter(routers.SimpleRouter):
    """
    A modified SimpleRouter that provides relationship and related resource
    routes. Provides an additional `relname` lookup.
    """

    routes = routers.SimpleRouter.routes + [
        routers.Route(
            url=r'^{prefix}/{lookup}/relationships/{relname}{trailing_slash}$',
            mapping={
                'get': 'retrieve_relationship',
                'post': 'create_relationship',
                'patch': 'update_relationship',
                'delete': 'destroy_relationship',
            },
            name='{basename}-relationship',
            initkwargs={'suffix': 'Relationship'},
        ),
        # TODO: add related route views
        # routers.Route(
        #     url=r'^{prefix}/{lookup}/{relname}{trailing_slash}$',
        #     mapping={
        #         'get': 'retrieve_or_list_related',
        #         'post': 'create_related',
        #         'put': 'update_related',
        #         'patch': 'partial_update_related',
        #         'delete': 'destroy_related',
        #     },
        #     name='{basename}-related',
        #     initkwargs={'suffix': 'Related Data'},
        # ),
        # routers.Route(
        #     url=r'^{prefix}/{lookup}/{relname}/{related_lookup}{trailing_slash}$',
        #     mapping={
        #         'get': 'retrieve_related',
        #         'put': 'update_related',
        #         'patch': 'partial_update_related',
        #         'delete': 'destroy_related',
        #     },
        #     name='{basename}-related',
        #     initkwargs={'suffix': 'Related Data'},
        # ),
    ]

    def get_related_regex(self, viewset):
        """
        Given a viewset, return the portion of URL regex that is used
        to match against a relationship on an instance.
        """
        base_regex = '(?P<{relname_url_kwarg}>{relname_regex})'
        relname_url_kwarg = getattr(viewset, 'relname_url_kwarg', 'relname')
        relname_regex = getattr(viewset, 'relname_regex', '[^/.]+')
        return base_regex.format(
            relname_url_kwarg=relname_url_kwarg,
            relname_regex=relname_regex,
        )

    def get_related_lookup_regex(self, viewset):
        """
        Given a viewset, return the portion of URL regex that is used
        to match against a related lookup of an instance.
        """
        base_regex = '(?P<{related_lookup_url_kwarg}>{related_lookup_regex})'
        related_lookup_url_kwarg = getattr(viewset, 'related_lookup_url_kwarg', 'related_pk')
        related_lookup_regex = getattr(viewset, 'related_lookup_regex', '[^/.]+')
        return base_regex.format(
            related_lookup_url_kwarg=related_lookup_url_kwarg,
            related_lookup_regex=related_lookup_regex,
        )

    def get_urls(self):
        """
        Use the registered viewsets to generate a list of URL patterns.

        Note that this overrides `SimpleRouter.get_urls()`, as there is no
        way to hook into the route format kwargs.
        """
        ret = []

        for prefix, viewset, basename in self.registry:
            lookup = self.get_lookup_regex(viewset)
            routes = self.get_routes(viewset)
            relname = self.get_related_regex(viewset)
            related_lookup = self.get_related_lookup_regex(viewset)

            for route in routes:

                # Only actions which actually exist on the viewset will be bound
                mapping = self.get_method_map(viewset, route.mapping)
                if not mapping:
                    continue

                # Build the url pattern
                regex = route.url.format(
                    prefix=prefix,
                    lookup=lookup,
                    trailing_slash=self.trailing_slash,
                    relname=relname,
                    related_lookup=related_lookup,
                )
                view = viewset.as_view(mapping, **route.initkwargs)
                name = route.name.format(basename=basename)
                ret.append(url(regex, view, name=name))

        return ret


class APIRouter(routers.DefaultRouter, BaseAPIRouter):
    """
    """
    include_format_suffixes = False

    def get_api_root_view(self):
        """
        Return a view to use as the API root.
        """
        api_root_dict = OrderedDict()
        list_name = self.routes[0].name
        for prefix, viewset, basename in self.registry:
            api_root_dict[prefix] = list_name.format(basename=basename)

        class APIRoot(views.APIView):
            _ignore_model_permissions = True

            def get(self, request, *args, **kwargs):
                links = OrderedDict((
                    ('self', request.build_absolute_uri()),
                ))
                for key, url_name in api_root_dict.items():
                    try:
                        links[key] = reverse(
                            url_name,
                            request=request,
                        )
                    except NoReverseMatch:
                        # Don't bail out if eg. no list routes exist, only detail routes.
                        continue

                ret = OrderedDict((
                    ('links', links),
                ))

                return Response(ret)

        return APIRoot.as_view()

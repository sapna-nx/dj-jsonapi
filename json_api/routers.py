
from collections import OrderedDict
from rest_framework import routers
from rest_framework.response import Response
from django.core.urlresolvers import NoReverseMatch
from .views import ResourceView
from .utils import reverse


class APIRouter(routers.DefaultRouter):
    include_format_suffixes = False

    def get_api_root_view(self):
        """
        Return a view to use as the API root.
        """
        api_root_dict = OrderedDict()
        list_name = self.routes[0].name
        for prefix, viewset, basename in self.registry:
            api_root_dict[prefix] = list_name.format(basename=basename)

        class APIRoot(ResourceView):
            _ignore_model_permissions = True

            def get(self, request, *args, **kwargs):
                ret = OrderedDict()
                for key, url_name in api_root_dict.items():
                    try:
                        ret[key] = reverse(
                            url_name,
                            request=request,
                        )
                    except NoReverseMatch:
                        # Don't bail out if eg. no list routes exist, only detail routes.
                        continue

                return Response(ret)

        return APIRoot.as_view()
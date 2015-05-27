
from rest_framework import viewsets
from . import views, mixins


class GenericResourceViewSet(viewsets.ViewSetMixin, views.ResourceView):
    pass


class ReadOnlyResourceViewSet(mixins.RetrieveResourceMixin,
                              mixins.ListResourceMixin,
                              GenericResourceViewSet):
    pass


class ResourceViewSet(mixins.CreateResourceMixin,
                      mixins.RetrieveResourceMixin,
                      mixins.UpdateResourceMixin,
                      mixins.DestroyResourceMixin,
                      mixins.ListResourceMixin,
                      GenericResourceViewSet):
    pass


from rest_framework import viewsets
from . import views, mixins


class GenericResourceViewSet(viewsets.ViewSetMixin, views.ResourceView):
    pass


class ReadOnlyResourceViewSet(mixins.RetrieveResourceMixin,
                              mixins.ListResourceMixin,
                              mixins.RetrieveRelationshipMixin,
                              GenericResourceViewSet):
    pass


class ResourceViewSet(mixins.CreateResourceMixin,
                      mixins.RetrieveResourceMixin,
                      mixins.UpdateResourceMixin,
                      mixins.DestroyResourceMixin,
                      mixins.ListResourceMixin,
                      mixins.RetrieveRelationshipMixin,
                      mixins.ManageRelationshipMixin,
                      GenericResourceViewSet):
    pass

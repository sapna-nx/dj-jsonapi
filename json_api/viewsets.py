
from rest_framework.viewsets import ViewSetMixin
from . import generics, mixins


class GenericResourceViewSet(ViewSetMixin, generics.GenericResourceView):
    pass


class ReadOnlyResourceViewSet(mixins.RetrieveResourceMixin,
                              mixins.ListResourceMixin,
                              mixins.RetrieveRelatedResourceMixin,
                              mixins.RetrieveRelationshipMixin,
                              GenericResourceViewSet):
    pass


class ResourceViewSet(mixins.CreateResourceMixin,
                      mixins.RetrieveResourceMixin,
                      mixins.UpdateResourceMixin,
                      mixins.DestroyResourceMixin,
                      mixins.ListResourceMixin,
                      mixins.RetrieveRelatedResourceMixin,
                      mixins.ManageRelatedResourceMixin,
                      mixins.RetrieveRelationshipMixin,
                      mixins.ManageRelationshipMixin,
                      GenericResourceViewSet):
    pass

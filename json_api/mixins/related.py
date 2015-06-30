
from rest_framework.response import Response


class RetrieveRelatedResourceMixin(object):
    def list_or_retrieve_related(self, request, pk, relname, *args, **kwargs):
        instance = self.get_object()
        rel = self.get_relationship(relname)

        # Handle to-one relationships. In the case where the related object does not
        # exist, we need return a 'null' response instead of a 404.
        if not rel.info.to_many:

            # we need to use field.attname in order to get just the pk, instead of the
            # full related instance.
            field = instance._meta.get_field(rel.attname)
            related_pk = None
            if hasattr(field, "attname"):
                related_pk = getattr(instance, field.attname, None)
            else:
                accessor_name = self.get_related_accessor_name(rel, instance)
                related_pk = getattr(instance, accessor_name).pk

            if related_pk is None:
                response_data = self.build_response_body(
                    links=self.get_default_links(),
                    data=None,
                )
                return Response(response_data)

            else:
                view = rel.viewset.__class__.as_view({'get': 'retrieve'})
                return view(request, pk=related_pk, *args, **kwargs)

        # Handle to-many relationships. In this case, we need to monkey patch the
        # existing `get_queryset()` so that it's filtered by the related quertyset.
        else:
            field = instance._meta.get_field(rel.attname)
            related_queryset = None
            if hasattr(field, "attname"):
                related_queryset = getattr(instance, field.attname, None).all()
            else:
                accessor_name = self.get_related_accessor_name(rel, instance)
                related_queryset = getattr(instance, accessor_name).all()

            view_class = self.related_viewset(rel.viewset.__class__, related_queryset)
            view = view_class.as_view({'get': 'list'})

            return view(request)

    def retrieve_related(self, request, pk, relname, related_pk, *args, **kwargs):
        rel = self.get_relationship(relname)
        view = rel.viewset.__class__.as_view({'get': 'retrieve'})
        return view(request, pk=related_pk, *args, **kwargs)

    def related_viewset(self, view_class, related_queryset):

        class RelatedViewSet(view_class):
            def get_queryset(self):
                return super(RelatedViewSet, self).get_queryset() & related_queryset

        return RelatedViewSet


class ManageRelatedResourceMixin(object):
    # POST's can be handled by updating the relationship data to include a pointer to the
    # parent. Then, just call the regular `create()` method.
    # `PATCH`ing shouldn't need to care about relationships.
    # `DELETE`ing shouldn't need to care about relationships either.
    pass

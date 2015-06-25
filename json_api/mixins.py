
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from json_api.exceptions import ParseError, PermissionDenied, Conflict, MethodNotAllowed


class CreateResourceMixin(object):
    """
    Create a resource instance.
    """
    def create(self, request, *args, **kwargs):
        try:
            data = request.data['data']
        except KeyError:
            raise ParseError('Primary \'data\' key not found in request data.')

        # Until a solution for content negotiation of extensions has been
        # determined, don't handle bulk creation
        # TODO: raise `APIError`s
        if isinstance(data, list):
            raise NotImplementedError('Bulk extension is not currently supported.')

        obj = self.perform_create(data)
        data = self.build_resource(obj)

        headers = self.get_success_headers(data)
        response_data = self.build_response_body(
            data=data,
        )
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

    @transaction.atomic
    def perform_create(self, data):
        if 'id' in data:  # and not self.allow_client_generated_ids:
            raise PermissionDenied('Client-Generated IDs are not supported.')

        if 'type' not in data:
            raise ParseError('Resource type not specified')
        if data['type'] != self.get_resource_type():
            raise Conflict('Resource type mismatch')

        serializer = self.get_serializer(data=data.get('attributes', {}))
        serializer.is_valid(raise_exception=True)

        # to-many relationships should be deferred since it implies m2m or a reverse FK.
        relationships = dict()
        deferred_relationships = dict()
        for relname, reldata in data.get('relationships', {}).items():
            rel = self.get_relationship(relname)

            try:
                reldata = reldata['data']
            except KeyError:
                raise ParseError('Relationship \'data\' object not found in request data for \'%s\'.' % relname)

            related = self.get_related_from_data(rel, reldata)

            # check permissions and determine if deferred
            if rel.info.to_many:
                for related_object in related:
                    rel.viewset.check_object_permissions(self.request, related_object)
                deferred_relationships[rel] = related
            else:
                rel.viewset.check_object_permissions(self.request, related)
                relationships[relname] = related

        instance = serializer.save(**relationships)

        for rel, related in deferred_relationships.items():
            return self.link_related(rel, instance, related)

        return instance

    def get_success_headers(self, data):
        try:
            return {'Location': data['links']['self']}
        except (TypeError, KeyError):
            return {}


class ListResourceMixin(object):
    """
    List a queryset of resources.
    """
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        self.page = page
        if page is not None:
            data = [self.build_resource(instance) for instance in page]
        else:
            data = [self.build_resource(instance) for instance in queryset]

        links = self.get_default_links()
        links.update(self.get_collection_actions())

        response_data = self.build_response_body(
            links=links,
            data=data,
        )
        return Response(response_data)


class RetrieveResourceMixin(object):
    """
    Retrieve a model instance.
    """
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        links = self.get_default_links()
        data = self.build_resource(instance)

        response_data = self.build_response_body(
            links=links,
            data=data,
        )
        return Response(response_data)


class UpdateResourceMixin(object):
    """
    Update a model instance.
    """
    def update(self, request, *args, **kwargs):
        try:
            data = request.data['data']
        except KeyError:
            raise ParseError('Primary \'data\' key not found in request data.')

        partial = kwargs.pop('partial', False)

        # TODO: raise `APIError`s
        if isinstance(data, list):
            raise NotImplementedError('Bulk extension is not currently supported.')

        obj = self.perform_update(data, partial)
        data = self.build_resource(obj)
        links = self.get_default_links()

        response_data = self.build_response_body(
            links=links,
            data=data,
        )
        return Response(response_data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @transaction.atomic
    def perform_update(self, data, partial=False):
        instance = self.get_object()

        if 'id' not in data:
            raise ParseError('Resource ID not specified')
        if data['id'] != instance.pk:
            raise Conflict('Resource ID mismatch')

        if 'type' not in data:
            raise ParseError('Resource type not specified')
        if data['type'] != self.get_resource_type():
            raise Conflict('Resource type mismatch')

        serializer = self.get_serializer(
            instance=instance,
            data=data.get('attributes', {}),
            partial=partial
        )
        serializer.is_valid(raise_exception=True)

        relationships = dict()
        for relname, reldata in data.get('relationships', {}).items():
            rel = self.get_relationship(relname)

            try:
                reldata = reldata['data']
            except KeyError:
                raise ParseError('Relationship \'data\' object not found in request data for \'%s\'.' % relname)

            related = self.get_related_from_data(rel, reldata)
            relationships[rel] = related

            # check permissions
            if rel.info.to_many:
                for related_object in related:
                    rel.viewset.check_object_permissions(self.request, related_object)
            else:
                rel.viewset.check_object_permissions(self.request, related)

        instance = serializer.save()

        for rel, related in relationships.items():
            return self.set_related(rel, instance, related)

        return instance


class DestroyResourceMixin(object):
    """
    Destroy a model instance.
    """
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()


class RetrieveRelationshipMixin(object):
    def retrieve_relationship(self, request, pk, relname, *args, **kwargs):
        instance = self.get_object()
        rel = self.get_relationship(relname)
        response_data = self.build_relationship_object(rel, instance, include_linkage=True)
        return Response(response_data)


class ManageRelationshipMixin(object):
    def create_relationship(self, request, pk, relname, *args, **kwargs):
        data = request.data['data']
        rel = self.get_relationship()
        if not rel.info.to_many:
            raise MethodNotAllowed()

        self.perform_relationship_create(data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update_relationship(self, request, pk, relname, *args, **kwargs):
        data = request.data['data']
        self.perform_relationship_update(data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy_relationship(self, request, pk, relname, *args, **kwargs):
        data = request.data['data']
        rel = self.get_relationship(relname)
        if not rel.info.to_many:
            raise MethodNotAllowed()

        self.perform_relationship_destroy(data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_relationship_create(self, data):
        instance = self.get_object()
        rel = self.get_relationship()
        related = self.get_related_from_data(rel, data)

        return self.link_related(rel, instance, related)

    def perform_relationship_update(self, data):
        instance = self.get_object()
        rel = self.get_relationship()
        related = self.get_related_from_data(rel, data)

        return self.set_related(rel, instance, related)

    def perform_relationship_destroy(self, data):
        instance = self.get_object()
        rel = self.get_relationship()
        related = self.get_related_from_data(rel, data)

        return self.unlink_related(rel, instance, related)


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

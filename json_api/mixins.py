
from __future__ import unicode_literals
# from collections import OrderedDict
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response


class CreateResourceMixin(object):
    """
    Create a resource instance.
    """
    def create(self, request, *args, **kwargs):
        data = request.data['data']

        # Until a solution for content negotiation of extensions has been
        # determined, don't handle bulk creation
        # TODO: raise `APIError`s
        if isinstance(data, list):
            raise NotImplementedError('Bulk extension is not currently supported.')

        response_data = self.perform_create(data)

        headers = self.get_success_headers(response_data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

    @transaction.atomic
    def perform_create(self, data):
        if 'id' in data:
            # Raise 403
            raise NotImplementedError('Client-Generated IDs are not currently supported.')

        if data['type'] != self.get_resource_type():
            # Raise 409 Conflict
            # TODO: Make mo betta
            raise Exception('409 Conflict - incorrect type')

        serializer = self.get_serializer(data=data.get('attributes', {}))
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        for rel in data.get('relationships', {}):
            raise NotImplementedError('Resource linkage on creation not currently supported.')

        return self.build_resource(obj)

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
        return Response(data)


class RetrieveResourceMixin(object):
    """
    Retrieve a model instance.
    """
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = self.build_resource(instance)
        return Response(data)


class UpdateResourceMixin(object):
    """
    Update a model instance.
    """
    def update(self, request, *args, **kwargs):
        data = request.data['data']
        partial = kwargs.pop('partial', False)

        # TODO: raise `APIError`s
        if isinstance(data, list):
            raise NotImplementedError('Bulk extension is not currently supported.')

        response_data = self.perform_update(data, partial)

        return Response(response_data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @transaction.atomic
    def perform_update(self, data, partial=False):
        instance = self.get_object()

        if data['id'] != instance.pk:
            raise Exception('409 Conflict - ID mismatch or something')

        if data['type'] != self.get_resource_type():
            # Raise 409 Conflict
            # TODO: Make mo betta
            raise Exception('409 Conflict - incorrect type')

        serializer = self.get_serializer(
            instance=instance,
            data=data.get('attributes', {}),
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        for rel in data.get('relationships', {}):
            raise NotImplementedError('Resource linkage on creation not currently supported.')

        return self.build_resource(obj)


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
    def retrieve_relationship(self, request, *args, **kwargs):
        return Response()


class ManageRelationshipMixin(object):
    def create_relationship(self, request, *args, **kwargs):
        return Response()

    def update_relationship(self, request, *args, **kwargs):
        return Response()

    def delete_relationship(self, request, *args, **kwargs):
        return Response()

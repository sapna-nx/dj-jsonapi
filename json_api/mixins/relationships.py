
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from json_api.exceptions import MethodNotAllowed


class RetrieveRelationshipMixin(object):
    def retrieve_relationship(self, request, pk, relname, *args, **kwargs):
        instance = self.get_object()
        rel = self.get_relationship(relname)
        response_data = self.build_relationship_object(rel, instance, include_linkage=True)
        return Response(response_data)


class ManageRelationshipMixin(object):
    def create_relationship(self, request, pk, relname, *args, **kwargs):
        data = self.get_data(request)
        rel = self.get_relationship()
        if not rel.info.to_many:
            raise MethodNotAllowed()

        self.perform_relationship_create(data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update_relationship(self, request, pk, relname, *args, **kwargs):
        data = self.get_data(request)
        self.perform_relationship_update(data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy_relationship(self, request, pk, relname, *args, **kwargs):
        data = self.get_data(request)
        rel = self.get_relationship(relname)
        if not rel.info.to_many:
            raise MethodNotAllowed()

        self.perform_relationship_destroy(data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic
    def perform_relationship_create(self, data):
        instance = self.get_object()
        rel = self.get_relationship()
        related = self.get_related_from_data(rel, data)

        self.link_related(rel, instance, related)
        instance.save()

    @transaction.atomic
    def perform_relationship_update(self, data):
        instance = self.get_object()
        rel = self.get_relationship()
        related = self.get_related_from_data(rel, data)

        self.set_related(rel, instance, related)
        instance.save()

    @transaction.atomic
    def perform_relationship_destroy(self, data):
        instance = self.get_object()
        rel = self.get_relationship()
        related = self.get_related_from_data(rel, data)

        self.unlink_related(rel, instance, related)
        instance.save()

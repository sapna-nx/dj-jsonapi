
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from json_api import exceptions


class CreateResourceMixin(object):
    """
    Create a resource instance.
    """
    def create(self, request, *args, **kwargs):
        data = self.get_data(request.data)

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
        self.validate_identity(data)

        serializer = self.get_serializer(data=data.get('attributes', {}))
        serializer.is_valid(raise_exception=True)

        # to-many relationships should be deferred since it implies m2m or a reverse FK.
        relationships = dict()
        deferred_relationships = dict()
        for relname, reldoc in data.get('relationships', {}).items():
            rel = self.get_relationship(relname)
            reldata = self.get_reldata(reldoc, relname)

            related = self.get_related_from_data(rel, reldata)

            # check permissions and determine if deferred
            if rel.info.to_many:
                for related_object in related:
                    rel.viewset.check_object_permissions(self.request, related_object)
                deferred_relationships[rel] = related
            else:
                rel.viewset.check_object_permissions(self.request, related)

                # reverse relationships need to be deferred, as they cannot be
                # used during object construction
                if rel.attname in self.model_info.reverse_relations:
                    deferred_relationships[rel] = related
                else:
                    relationships[rel.attname] = related

        instance = serializer.save(**relationships)

        for rel, related in deferred_relationships.items():
            self.set_related(rel, instance, related)

            # deferred/reverse to-one relationships need to be saved
            if not rel.info.to_many:
                related.save()

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

        include_paths = self.get_include_paths(queryset)

        page = self.paginate_queryset(queryset)
        self.page = page
        if page is not None:
            data = [self.build_resource(instance) for instance in page]
            included_data = self.get_included_data(page, include_paths).values()

        else:
            data = [self.build_resource(instance) for instance in queryset]
            included_data = self.get_included_data(queryset, include_paths).values()

        links = self.get_default_links()
        links.update(self.get_collection_actions())

        body = {
            'links': links,
            'data': data,
        }

        if included_data:
            body['included'] = included_data

        response_data = self.build_response_body(**body)
        return Response(response_data)


class RetrieveResourceMixin(object):
    """
    Retrieve a model instance.
    """
    def retrieve(self, request, *args, **kwargs):
        # TODO:
        # queryset optimization hooks into `get_object()`
        instance = self.get_object()
        paths = self.get_include_paths(self.get_queryset())

        links = self.get_default_links()
        data = self.build_resource(instance)
        included_data = self.get_included_data(instance, paths).values()

        body = {
            'links': links,
            'data': data,
        }

        if included_data:
            body['included'] = included_data

        response_data = self.build_response_body(**body)
        return Response(response_data)


class UpdateResourceMixin(object):
    """
    Update a model instance.
    """
    def update(self, request, *args, **kwargs):
        data = self.get_data(request.data)

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
        self.validate_identity(data, instance)

        serializer = self.get_serializer(
            instance=instance,
            data=data.get('attributes', {}),
            partial=partial
        )
        serializer.is_valid(raise_exception=True)

        relationships = dict()
        for relname, reldoc in data.get('relationships', {}).items():
            rel = self.get_relationship(relname)
            reldata = self.get_reldata(reldoc, relname)

            related = self.get_related_from_data(rel, reldata)
            relationships[rel] = related

            # check permissions
            if rel.info.to_many:
                for related_object in related:
                    rel.viewset.check_object_permissions(self.request, related_object)
            else:
                rel.viewset.check_object_permissions(self.request, related)

        instance = serializer.save()

        rel_errors = []
        for rel, related in relationships.items():
            try:
                self.set_related(rel, instance, related)
            except exceptions.APIError as e:
                source = e._data.get('source') or {}
                pointer = '/data/relationships/%s' % (source.get('pointer', ''))
                source['pointer'] = pointer
                e._data['source'] = source
                rel_errors.append(e)
        if rel_errors:
            raise exceptions.ErrorList(rel_errors)

        instance.save()

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

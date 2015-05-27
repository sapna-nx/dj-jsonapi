
import six
from collections import OrderedDict
from rest_framework.generics import GenericAPIView
from rest_framework.utils import field_mapping
# from rest_framework.utils import model_meta
from .utils import import_class, reverse


class ResourceView(GenericAPIView):
    relationships = None

    def get_top_links(self):
        links = OrderedDict([('self', self.request.build_absolute_uri()), ])

        if getattr(self, 'page', None):
            links.update(self.paginator.get_links())

        return links

    def get_resource_type(self, model=None):
        """
        Returns the resource type for a given model. Currently this defaults to
        the verbose_name of the model.

        If no model is given, the model associated with the view is used.
        """
        if model is None:
            model = self.get_serializer_class().Meta.model
        return model._meta.verbose_name

    def get_resource_links(self, instance):
        """
        Returns a links object for a resource in conformance with:
        http://jsonapi.org/format/#document-structure-structure-resource-object-links

        Additionally, it includes any detail routes attached to the viewset.
        """
        view_name = field_mapping.get_detail_view_name(instance)
        data = OrderedDict((
            ('self', reverse(view_name, self.request, args=(instance.pk, ))),
        ))

        # TODO: add in dynamic `@detail_route` routes
        return data

    def get_resource_meta(self, instance):
        pass

    def build_resource(self, instance):
        """
        Returns a resource object for a model instance, in conformance with:
        http://jsonapi.org/format/#document-structure-resource-objects
        """
        serializer = self.get_serializer(instance)
        data = OrderedDict((
            ('id', instance.pk),
            ('type', self.get_resource_type(instance)),
        ))

        attributes = serializer.data
        relationships = self.get_relationship_objects()
        links = self.get_resource_links(instance)
        meta = self.get_resource_meta(instance)

        if attributes:
            data['attributes'] = attributes
        if relationships:
            data['relationships'] = relationships
        if links:
            data['links'] = links
        if meta:
            data['meta'] = meta

        return data

    def build_resource_identifier(self, instance):
        """
        Returns a resource identifier object for a model instance, in conformance with:
        http://jsonapi.org/format/#document-structure-resource-identifier-objects
        """
        data = OrderedDict((
            ('id', instance.pk),
            ('type', self.get_resource_type(instance)),
        ))

        meta = self.get_resource_meta(instance)
        if meta:
            data['meta'] = meta

        return data

    def get_relname(self, rel):
        """
        Returns the relationship name used to represent the relationship.
        Defaults to the `accessor_name` unless a `relname` is provided.
        """
        return rel.get('relname', rel['accessor_name'])

    def get_viewset(self, rel):
        """
        Returns the viewset for the givent relationship. Resolves class paths.
        """
        viewset = rel['viewset']
        if isinstance(viewset, six.string_types):
            return import_class(viewset)
        return viewset

    def get_relationship_links(self, rel):
        relname = self.get_relname(rel)

        return OrderedDict((
            ('self', self.request.build_absolute_uri('relationships/%s' % relname)),
            ('related', self.request.build_absolute_uri(relname)),
        ))

    def get_relationship_linkage(self, rel):
        # obj = self.get_object()
        # viewset = self.get_viewset(rel)
        pass

    def get_relationship_meta(self, rel):
        pass

    def get_relationship_objects(self):
        """
        Returns a dictionary of {relname: relationship object}
        This is defined by: http://jsonapi.org/format/#document-structure-links

        This function expects the view to have a `relationships` attribute containing a
        list of dictionaries containing the following keys:

        - accessor_name: The name used to access the field on the underlying model. This
          value is passed to the model meta's `get_field` method.
        - relname (optional): The  name to use for the relationship. This is functionally
          an alias for, and defaults to, the `accessor_name`. Useful for overriding
          automatically generated accessor names.
        - viewset: The viewset to use for controlling access to the related object set.
          Acceptable values are either the viewset or a class path to the viewset. The
          class path can either use a dot or colon seperator to delimit the class name.

        Currently, relationship objects only contain the `links` key. `linkage` and
        `meta` may be overridden.

        """
        if not self.relationships:
            return None

        rel_objects = OrderedDict()
        for rel in self.relationships:
            rel_object = OrderedDict((
                ('links', self.get_relationship_links(rel)),
            ))

            data = self.get_relationship_linkage(rel)
            if data:
                rel_object['data'] = data

            meta = self.get_relationship_meta(rel)
            if meta:
                rel_object['meta'] = meta

            rel_objects[self.get_relname(rel)] = rel_object
        return rel_objects

    def _get_rel_definition(self, relname):
        """
        Returns the relationship definition for a given relationship name.
        """
        for rel in self.relationships:
            if self.get_relname(rel) == relname:
                return rel
        return None

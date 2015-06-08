
from collections import OrderedDict
from django.db.models.query import QuerySet
from rest_framework.generics import GenericAPIView
from rest_framework.utils import field_mapping

from json_api.utils import model_meta
from json_api.utils.reverse import reverse
from json_api.utils.rels import resolved_rel
from json_api import serializers, views


class GenericResourceView(views.ResourceView, GenericAPIView):

    def __init__(self, *args, **kwargs):
        super(GenericResourceView, self).__init__(*args, **kwargs)

        model = self.get_serializer_class().Meta.model
        self.model_info = model_meta.get_field_info(model)

    def resolve_relationships(self, relationships):
        return [resolved_rel(
            info=self.model_info.relations[rel.attname],
            request=self.request,
            **rel._asdict()
        ) for rel in relationships]

    def get_serializer_class(self, relname=None):
        # if a relname isn't supplied, try to fetch from the view kwargs.
        if relname is None:
            # kwargs may not be set if this viewset is being accessed by
            # another vieweset.
            relname = getattr(self, 'kwargs', {}).get(self.relname_url_kwarg)

        if relname is not None:
            rel = self.get_relationship(relname)

            # TODO: decide if this amount of coupling between the router and
            # view is okay. Consider hyperlinked serializers as an example.
            if self.request.resolver_match.url_name.endswith('-relationship'):
                return self.get_identity_serializer(rel)

            elif self.request.resolver_match.url_name.endswith('-related'):
                return self.get_related_serializer(rel)

        return super(GenericResourceView, self).get_serializer_class()

    def get_identity_serializer(self, rel):
        """
        Returns a serializer for a relationship that is suitable for
        representing its resource identifiers.
        """
        class ResourceRelationshipIdentifier(serializers.ResourceIdentifierSerializer):
            class Meta:
                model = rel.viewset.get_serializer_class().Meta.model

        return ResourceRelationshipIdentifier

    def get_related_serializer(self, rel):
        """
        Returns the serializer used by a related resource.
        """
        # TODO: this is correct, right?
        return rel.viewset.get_serializer_class()

    def get_default_links(self):
        """
        The default top-level links for the current request. Contains the
        `self` link for the current request, as well pagination links if
        applicable.
        """
        links = super(GenericResourceView, self).get_default_links()

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
        links = OrderedDict((
            ('self', reverse(view_name, self.request, args=(instance.pk, ))),
        ))

        links.update(self.get_resource_actions(instance.pk))
        return links

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
        relationships = self.get_relationship_objects(instance)
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

    def get_relationship_links(self, rel, instance):
        return OrderedDict((
            ('self', reverse(
                '%s-relationship' % self.get_basename(),
                self.request,
                args=[instance.pk, rel.relname]
            )),
            # ('related', self.request.build_absolute_uri(relname)),
        ))

    def get_relationship_linkage(self, rel, instance):
        # don't forget to paginate the queryset
        related = self.get_related_object(rel, instance)

        if related is None:
            return None

        if not isinstance(related, QuerySet):
            return OrderedDict((
                ('id', related.pk),
                ('type', self.get_resource_type(related)),
            ))

        serializer_class = self.get_identity_serializer(rel)
        return serializer_class(related.only('pk'), many=True).data

    def get_relationship_meta(self, rel):
        pass

    def build_relationhsip_object(self, rel, instance, include_linkage=False):
        """
        Builds a relationship object that represents to-one and to-many
        relationships between the primary resource and related resources.
        This conforms to the "relationship object" described under:
        http://jsonapi.org/format/#document-structure-resource-objects-relationships

        Set `include_linkage` to include relationship linkage data in the
        request.

        Note:
        Paginated data is only supported for the primary request resource.
        Because of this, linkage for to-many relationships should NOT be
        included outside of a specific relationship request.

        ie, do not include linkage for /api/books/1. Do include linkage
        for /api/books/1/authors.

        """
        rel_object = OrderedDict((
            ('links', self.get_relationship_links(rel, instance)),
        ))

        if include_linkage:
            data = self.get_relationship_linkage(rel, instance)
            rel_object['data'] = data

        meta = self.get_relationship_meta(rel)
        if meta:
            rel_object['meta'] = meta

        return rel_object

    def get_relationship_objects(self, instance):
        """
        Returns a dictionary of {relname: relationship object}
        This is defined by: http://jsonapi.org/format/#document-structure-links

        This object is suitable for displaying the relationship data on a resource object.
        Note that this excludes linkage for to-many relationships, as it may be 'large'
        and require pagination. DRF pagination is not supported for related querysets.

        This function expects the view to have a `relationships` attribute containing a
        list of dictionaries containing the following keys:

        - attname: The name used to access the field on the underlying model. This
          value is passed to the model meta's `get_field` method.
        - relname (optional): The  name to use for the relationship. This is functionally
          an alias for, and defaults to, the `attname`. Useful for overriding
          automatically generated accessor names.
        - viewset: The viewset to use for controlling access to the related object set.
          Acceptable values are either the viewset or a class path to the viewset. The
          class path can either use a dot or colon seperator to delimit the class name.

        Currently, relationship objects only contain the `links` key. `linkage` and
        `meta` may be overridden.

        """
        if not self.relationships:
            return None

        return OrderedDict([(
            rel.relname,
            self.build_relationhsip_object(
                rel, instance, not rel.info.to_many
            )
        ) for rel in self.relationships])

    def get_related_object(self, rel, instance):
        """
        Returns a related object or queryset for a given relationship.
        You may want to override this if you need to provide non-standard
        queryset lookups.
        """
        # Perform the lookup filtering.
        queryset = rel.viewset.get_queryset()
        field = instance._meta.get_field(rel.attname)

        if rel.info.to_many:
            field_name = field.related.name
            return queryset.filter(**{field_name: instance.pk})

        else:
            field_name = field.field.name
            # It is possible that the relationship doesn't exist. In that
            # case, it is valid to return None
            try:
                related = queryset.get(**{field_name: instance.pk})
            except queryset.model.DoesNotExist:
                related = None

            # May raise a permission denied
            if related is not None:
                rel.viewset.check_object_permissions(self.request, related)

            return related

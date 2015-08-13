
import inspect
from collections import OrderedDict
from django.db.models.query import QuerySet
from django.db.models import Value, CharField
from django.utils import six
from rest_framework.generics import GenericAPIView

from json_api.utils import model_meta, import_class
from json_api.utils.reverse import reverse
from json_api.utils.rels import model_rel
from json_api.exceptions import PermissionDenied
from json_api.settings import api_settings
from json_api import serializers, views


class GenericResourceView(views.ResourceView, GenericAPIView):
    inclusion_class = api_settings.DEFAULT_INCLUSION_CLASS

    def __init__(self, *args, **kwargs):
        super(GenericResourceView, self).__init__(*args, **kwargs)

        model = self.get_serializer_class().Meta.model
        self.model_info = model_meta.get_field_info(model)

    def resolve_relationships(self, relationships):
        if not relationships:
            return []
        return [model_rel(
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
        serializer_class = rel.viewset.get_serializer_class()
        identifier_class = {
            True: serializers.PolymorphicResourceIdentifierSerializer,
            False: serializers.ResourceIdentifierSerializer,
        }[issubclass(serializer_class, serializers.PolymorphicResourceSerializer)]

        class ResourceRelationshipIdentifier(identifier_class):
            class Meta(serializer_class.Meta):
                pass

        return ResourceRelationshipIdentifier

    def get_related_serializer(self, rel):
        """
        Returns the serializer used by a related resource.
        """
        # TODO: this is correct, right?
        return rel.viewset.get_serializer_class()

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            'request': self.request,
            'view': self
        }

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
        view_name = "%s-detail" % self.get_basename()
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
            ('links', self.get_resource_links(instance)),
            ('attributes', serializer.data),
            ('relationships', self.get_relationship_objects(instance)),
            ('meta', self.get_resource_meta(instance)),
        ))

        for key, value in data.items():
            if not value:
                del data[key]

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
            ('related', reverse(
                '%s-related' % self.get_basename(),
                self.request,
                args=[instance.pk, rel.relname]
            )),
        ))

    def get_relationship_linkage(self, rel, instance):
        # don't forget to paginate the queryset
        related = self.get_related_data(rel, instance)

        if related is None:
            return None

        if not isinstance(related, QuerySet):
            # TODO: decide on whether we should use a serializer instead.
            return OrderedDict((
                ('id', related.pk),
                ('type', self.get_resource_type(related)),
            ))

        resource_type = self.get_resource_type(related.model)
        serializer_class = self.get_identity_serializer(rel)
        related = related.only('pk').annotate(type=Value(resource_type, CharField()))
        return serializer_class(related, many=True).data

    def get_relationship_meta(self, rel):
        pass

    def build_relationship_object(self, rel, instance, include_linkage=False):
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
            self.build_relationship_object(
                rel, instance, not rel.info.to_many
            )
        ) for rel in self.relationships])

    def get_related_queryset(self, rel):
        """
        Returns the queryset for the relationship descriptor.
        """
        return rel.viewset.get_queryset()

    def get_related_accessor_name(self, rel, model):
        """
        Get the accessor name for the given relationship on the model.
        """
        field = model._meta.get_field(rel.attname)

        # forward relationship
        if hasattr(field, 'attname'):
            return field.name

        # reverse relationship
        else:
            return field.get_accessor_name()

    def get_related_data(self, rel, instance):
        """
        Returns the related data for a given relationship. Depending on if the
        relationship is to-many, the returned data will either be a related
        object instance or a queryset.

        You may want to override this if you need to provide non-standard
        queryset lookups.
        """
        viewset_queryset = self.get_related_queryset(rel)

        if rel.info.to_many:
            accessor_name = self.get_related_accessor_name(rel, instance)
            related_queryset = getattr(instance, accessor_name).all()
            # TODO:
            # investigate why `related_queryset & viewset_queryset` produces
            # duplicates. This seems to be related to the annotation.
            return viewset_queryset & related_queryset

        else:
            accessor_name = self.get_related_accessor_name(rel, instance)
            related_object = getattr(instance, accessor_name, None)

            # It is possible that the relationship doesn't exist. In that
            # case, it is valid to return None
            if related_object is None:
                return None

            # check that the related object is in the viewset's queryset.
            # raises a 403 if not the related object is not in the queryset.
            # TODO: determine if this is the correct behavior
            if not viewset_queryset.filter(pk=related_object.pk).exists():
                raise PermissionDenied

            # May raise a permission denied
            rel.viewset.check_object_permissions(self.request, related_object)

            return related_object

    def get_related_from_data(self, rel, data):
        """
        Returns a model instance or queryset from a related viewset.
        """
        # TODO: validate polymorphic types and raise ValidationErrors where appropriate.
        # ie, If a parent type A has polymorphic subtypes B and C, then an instance of
        # type B can correctly be referred to as types A and B, but not C. The serializer
        # only has enough context to determine if the type is within the overall valid
        # set of {A, B, C}, but not whether it is consistent with its corresponding
        # instances' types.

        # None is valid value for to-one relationships
        if data is None and not rel.info.to_many:
            return None

        serializer = self.get_identity_serializer(rel)(data=data, many=rel.info.to_many)
        serializer.is_valid(raise_exception=True)

        if rel.info.to_many:
            related_pks = [related['id'] for related in serializer.validated_data]
            related = rel.info.related_model.objects.filter(pk__in=related_pks)

        else:
            related_pk = serializer.validated_data['id']
            related = rel.info.related_model.objects.get(pk=related_pk)

        return related

    @property
    def includer(self):
        """
        The includer instance associated with the view, or `None`.
        """
        if not hasattr(self, '_includer'):
            if self.inclusion_class is None:
                self._includer = None
            else:
                self._includer = self.inclusion_class()
        return self._includer

    def get_include_paths(self, queryset):
        """
        Get the relationship paths of the objects to be included.
        """
        if self.includer is None:
            return None
        return self.includer.get_include_paths(queryset, self.request, view=self)

    def get_included_data(self, data, paths):
        """
        Return the related data to be included in the response.
        """
        if self.includer is None:
            return None
        return self.includer.get_included_data(data, paths, self)

    def link_related(self, rel, instance, related):
        accessor_name = self.get_related_accessor_name(rel, instance)

        if rel.info.to_many:
            # check permissions first before assignment
            for related_object in related:
                rel.viewset.check_object_permissions(self.request, related_object)
            getattr(instance, accessor_name).add(*related)

        else:
            if not rel.info.model_field.null:
                raise PermissionDenied('\'%s\' does not allow null values.' % rel.relname)
            rel.viewset.check_object_permissions(self.request, related)
            setattr(instance, accessor_name, related)

    def unlink_related(self, rel, instance, related):
        # exit early if nothing to do
        if not related:
            return

        accessor_name = self.get_related_accessor_name(rel, instance)

        if rel.info.to_many:
            # If the ForeignKey is not nullable, raise 403
            manager = getattr(instance, accessor_name)
            if not hasattr(manager, 'remove'):
                raise PermissionDenied('\'%s\' does not allow null values.' % rel.relname)

            # check permissions first before assignment
            for related_object in related:
                rel.viewset.check_object_permissions(self.request, related_object)

            manager.remove(*related)

        else:
            rel.viewset.check_object_permissions(self.request, related)
            setattr(instance, accessor_name, None)

    def set_related(self, rel, instance, related):
        if rel.info.to_many:
            current = self.get_related_data(rel, instance)
            current = current.exclude(id__in=related)
            self.unlink_related(rel, instance, current)
        self.link_related(rel, instance, related)


class GenericPolymorphicResourceView(GenericResourceView):
    subtypes = None

    # todo: allow inclusion/selection of subtypes

    def build_resource(self, instance):
        """
        Returns a resource object for a model instance, in conformance with:
        http://jsonapi.org/format/#document-structure-resource-objects
        """
        data = super(GenericPolymorphicResourceView, self).build_resource(instance)

        viewset = self.get_subtype_viewset(data['type'])
        if not viewset:
            return data

        data['links']['subtype'] = viewset.get_resource_links(instance)['self']

        return data

    def get_subtype_viewset(self, subtype):
        if subtype not in self.subtypes:
            return None

        viewset = self.subtypes[subtype]

        if isinstance(viewset, six.string_types):
            viewset = import_class(viewset)

        if inspect.isclass(viewset):
            viewset = viewset()

        viewset.request = self.request
        return viewset

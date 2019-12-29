
from collections import OrderedDict
from django.db.models.query import QuerySet
from django.db.models import Value, CharField
from django.utils.functional import cached_property
from rest_framework.generics import GenericAPIView

from json_api.utils import model_meta
from json_api.utils.reverse import reverse
from json_api.utils.urls import unquote_brackets
from json_api.exceptions import PermissionDenied
from json_api.settings import api_settings
from json_api import serializers, views
from model_utils.managers import InheritanceQuerySet


class GenericResourceView(views.ResourceView, GenericAPIView):
    inclusion_class = api_settings.DEFAULT_INCLUSION_CLASS

    @cached_property
    def model_info(self):
        model = self.get_queryset().model
        return model_meta.get_field_info(model)

    def _try_resource(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup = self.kwargs.get(lookup_url_kwarg, None)

        if lookup is None:
            return None

        queryset = self.get_queryset()
        model = queryset.model

        try:
            return queryset.get(**{self.lookup_field: lookup})

        # Except missing instances, and invalid lookup values.
        # TODO: Maybe accept all exceptions?
        except (model.DoesNotExist, model.MultipleObjectsReturned, ValueError):
            return None

    def get_relationships(self):
        """
        Returns the relationship names associated with this view, mapped to
        their `rel` descriptors.
        """
        rels = super(GenericResourceView, self).get_relationships()
        for rel in list(rels.values()):
            rel.info = self.model_info.relations[rel.attname]

        return rels

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
                return rel.viewset.get_identity_serializer()

            elif self.request.resolver_match.url_name.endswith('-related'):
                return self.get_related_serializer(rel)

        return super(GenericResourceView, self).get_serializer_class()

    def get_identity_serializer(self):
        """
        Returns a serializer for a relationship that is suitable for
        representing its resource identifiers.
        """
        serializer_class = self.get_serializer_class()
        identifier_class = {
            True: serializers.PolymorphicResourceIdentifierSerializer,
            False: serializers.ResourceIdentifierSerializer,
        }[self.subtypes is not None]

        # build {model: serializer} class maps
        types = {}
        for subtype in list(self.get_subtypes().values()):
            cls = subtype.viewset.get_serializer_class()
            types[cls.Meta.model] = cls

        class ResourceRelationshipIdentifier(identifier_class):
            class Meta(serializer_class.Meta):
                subtypes = types or None

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
            'request': getattr(self, 'request', None),
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

        links = {name: unquote_brackets(link) for name, link in list(links.items())}

        return links

    def get_primary_type(self):
        model = self.get_queryset().model
        return self.get_resource_type(model)

    def get_resource(self):
        return self.get_object()

    def get_resource_id(self, instance):
        return getattr(instance, self.lookup_field)

    def get_resource_type(self, instance):
        """
        Returns the resource type for a given model. Currently this defaults to
        the verbose_name of the model.

        instance may be either a model class or an instance.
        """
        return model_meta.verbose_name(instance)

    def get_resource_attributes(self, instance):
        return self.get_serializer(instance).data

    def get_resource_links(self, instance):
        """
        Returns a links object for a resource in conformance with:
        http://jsonapi.org/format/#document-resource-object-links

        Additionally, it includes any detail routes attached to the viewset.
        """
        view_name = "%s-detail" % self.get_basename()
        resource_id = self.get_resource_id(instance)
        links = OrderedDict((
            ('self', reverse(view_name, self.request, args=(resource_id, ))),
        ))

        links.update(self.get_resource_actions(resource_id))

        # TODO: maybe move to HTML renderer?
        links = {name: unquote_brackets(link) for name, link in list(links.items())}

        return links

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
        serializer_class = rel.viewset.get_identity_serializer()
        related = related.only('pk').annotate(type=Value(resource_type, CharField()))

        # TODO: build object individually, similar to build_resource. This is
        # related to additional view handling, such as meta blocks.
        return serializer_class(related, many=True).data

    def get_relationship_meta(self, rel):
        pass

    def build_relationship_object(self, rel, instance, include_linkage=False):
        """
        Builds a relationship object that represents to-one and to-many
        relationships between the primary resource and related resources.
        This conforms to the "relationship object" described under:
        http://jsonapi.org/format/#document-resource-object-relationships

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

    def get_resource_relationships(self, instance, linkages=None):
        """
        Returns a dictionary of {relname: relationship object}
        This is defined by: http://jsonapi.org/format/#document-links

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
        if not self.get_relationships():
            return None

        if linkages is None:
            linkages = []

        return OrderedDict([(
            rel.relname,
            self.build_relationship_object(
                rel, instance, relname in linkages
            )
        ) for relname, rel in list(self.get_relationships().items())])

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
            print("related_object", related_object, accessor_name, rel.__dict__, instance)
            # It is possible that the relationship doesn't exist. In that
            # case, it is valid to return None
            if related_object is None:
                return None

            # check that the related object is in the viewset's queryset.
            # raises a 403 if not the related object is not in the queryset.
            # TODO: determine if this is the correct behavior
            # if not viewset_queryset.filter(pk=related_object.pk).exists():
            # refetch object, this allows us to handle polymorphic scenarios
            related_object_exists = viewset_queryset.filter(pk=related_object.pk)
            print(">>>>>>>>>>>>>>>>>>>>", related_object_exists, related_object_exists.__dict__)
            if related_object_exists is None:
                raise PermissionDenied
            if isinstance(related_object_exists, InheritanceQuerySet):
                related_object = viewset_queryset.filter(pk=related_object.pk).select_subclasses()
            else:
                related_object = viewset_queryset.filter(pk=related_object.pk).get()

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

        serializer = rel.viewset.get_identity_serializer()(data=data, many=rel.info.to_many)
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

    def group_include_paths(self, paths):
        """
        Group paths by their base path.
        """
        if self.includer is None:
            return None
        return self.includer.group_include_paths(paths)

    def link_related(self, rel, instance, related):
        if not rel.info.to_many:
            raise Exception('raise configuration error: to-one should not call link_related')

        accessor_name = self.get_related_accessor_name(rel, instance)

        # check permissions first before assignment
        for related_object in related:
            rel.viewset.check_object_permissions(self.request, related_object)
        getattr(instance, accessor_name).add(*related)

    def unlink_related(self, rel, instance, related):
        if not rel.info.to_many:
            raise Exception('raise configuration error: to-one should not call unlink_related')

        # exit early if nothing to do
        if not related:
            return

        accessor_name = self.get_related_accessor_name(rel, instance)

        # If the ForeignKey is not nullable, raise 403
        manager = getattr(instance, accessor_name)
        if not hasattr(manager, 'remove'):
            raise PermissionDenied('This field is required.', source={'pointer': rel.relname})

        # check permissions first before assignment
        for related_object in related:
            rel.viewset.check_object_permissions(self.request, related_object)

        manager.remove(*related)

    def set_related(self, rel, instance, related):
        current = self.get_related_data(rel, instance)

        if rel.info.to_many:
            current = current.exclude(id__in=related)
            self.unlink_related(rel, instance, current)
            self.link_related(rel, instance, related)
            return

        # handle to-one.
        rel.viewset.check_object_permissions(self.request, related)
        accessor_name = self.get_related_accessor_name(rel, instance)
        try:
            setattr(instance, accessor_name, related)
        except ValueError:
            raise PermissionDenied('This field is required.', source={'pointer': rel.relname})

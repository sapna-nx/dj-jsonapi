
import six
from collections import OrderedDict
from rest_framework.generics import GenericAPIView
from rest_framework.utils import field_mapping, model_meta
from .utils import import_class, reverse
from . import routers


class ResourceView(GenericAPIView):
    relationships = None

    def build_response_body(self, **kwargs):
        """
        Format the top-level repsonse body.
        """
        body = OrderedDict()

        # TODO: One of the following keys is required. There should
        # probably be an internal API error that's raised.
        # if not any(key in kwargs for key in ('data', 'errors', 'meta')):
        #     raise APIErrorOrSomething()

        for key in ('jsonapi', 'links', 'data', 'included', 'errors', 'meta'):
            if kwargs.get(key) is not None:
                body[key] = kwargs[key]
        return body

    def get_default_links(self):
        """
        The default links for the current request. Contains the `self` link
        for the current request, as well pagination links if applicable.
        """
        links = OrderedDict([
            ('self', self.request.build_absolute_uri()),
        ])

        if getattr(self, 'page', None):
            links.update(self.paginator.get_links())

        return links

    def _get_dynamic_views(self):
        detail_views = []
        list_views = []
        for methodname in dir(self.__class__):
            attr = getattr(self.__class__, methodname)
            httpmethods = getattr(attr, 'bind_to_methods', None)
            detail = getattr(attr, 'detail', True)
            if httpmethods:
                if detail:
                    detail_views.append(methodname.replace('_', '-'))
                else:
                    list_views.append(methodname.replace('_', '-'))

        return detail_views, list_views

    def get_detail_action_links(self, instance):
        base_name = self.get_basename()
        view_names = self._get_dynamic_views()[0]
        pk = instance.pk

        return OrderedDict(((
            view_name, reverse("%s-%s" % (base_name, view_name), self.request, args=[pk])
        ) for view_name in view_names))

    def get_list_action_links(self):
        base_name = self.get_basename()
        view_names = self._get_dynamic_views()[1]

        return OrderedDict(((
            view_name, reverse("%s-%s" % (base_name, view_name), self.request)
        ) for view_name in view_names))

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

        links.update(self.get_detail_action_links(instance))
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

    def get_basename(self):
        """
        The `basename` to use for reversing URLs. You may need to override
        this if you provide a base_name to your router.
        """
        # meh?
        self.__router = getattr(self, '__router', routers.BaseAPIRouter())
        return self.__router.get_default_base_name(self)

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

    def get_relationship(self, relname):
        """
        Returns the relationship for a given relationship name.
        """
        for rel in self.relationships:
            if relname == self.get_relname(rel):
                return rel

    def get_relationship_links(self, rel, instance):
        relname = self.get_relname(rel)

        return OrderedDict((
            ('self', reverse(
                '%s-relationship' % self.get_basename(),
                self.request,
                args=[instance.pk, relname]
            )),
            # ('related', self.request.build_absolute_uri(relname)),
        ))

    def get_relationship_linkage(self, rel, instance):
        # don't forget to paginate the queryset
        # info = model_meta.get_field_info(instance)
        # if info.relations[rel['accessor_name']].to_many:
        #     pass
        # viewset = self.get_viewset(rel)
        pass

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
            if data:
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

        info = model_meta.get_field_info(instance)

        return OrderedDict([(
            self.get_relname(rel),
            self.build_relationhsip_object(
                rel, instance, info.relations[rel['accessor_name']].to_many
            )
        ) for rel in self.relationships])


from collections import OrderedDict
from rest_framework.request import Request
from rest_framework.views import APIView
from json_api.utils.reverse import reverse
from json_api import routers, exceptions


class ResourceView(APIView):
    """
    Base class for all json-api views. Contains some base machinery necessary
    for resolving relationships and building json-api compliant responses.
    """
    # TODO: verify that `request = None` is safe. Does DRF ever rely on
    # the request attribute not being set? Should view code be rewritten to
    # not assume that requests exist?
    request = None
    relname_url_kwarg = 'relname'
    relationships = None
    subtypes = None

    allow_client_generated_ids = False

    # Dispatch methods

    def initialize_request(self, request, *args, **kwargs):
        # simply return the request if it has already been initialized.
        if isinstance(request, Request):
            return request
        return super(ResourceView, self).initialize_request(request, *args, **kwargs)

    # Blegh - this is a bit gross. We need to determine the requested resource
    # type so that the request can be re-dispatched to the appropriate subtype
    # view (if applicable). However,
    # - we cannot entirely rely on get_resource(), as this only works for
    #   existing instances. eg, POSTs would fail as their no resource yet.
    # - we cannot entirely rely on the incoming {data: type: ""}, as,
    #   - it's not always present (GET/DELETE)
    #   - it may represent a different resource (related resource data)
    def _get_requested_type(self):
        # try getting the resource as most requests are operating on an
        # existing resource.
        resource = self._try_resource()
        if resource is not None:
            return self.get_resource_type(resource)

        # try to get {data: type: ""} from the request's data.
        if 'data' in self.request.data and 'type' in self.request.data['data']:
            return self.request.data['data']['type']

    def _try_resource(self):
        # try to get the requested resource instance via URL parsing.
        raise NotImplementedError('`_try_resource()` must be implemented.')

    # Note: A caveat of this implementation is that the request is initialized
    # in the primary ResourceView and is passed to the dispatch method of the
    # heterogenous type's view. It is not entirely clear if this is desirable.
    def dispatch(self, request, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request

        reqtype = self._get_requested_type()
        subtype = self.get_subtypes().get(reqtype) if reqtype else None
        if subtype is not None:
            view_class = subtype.viewset.__class__
            view = view_class.as_view(self.action_map)
            return view(request, *args, **kwargs)

        return super(ResourceView, self).dispatch(request, *args, **kwargs)

    def get_primary_type(self):
        """
        Returns the primary type name accepted by this view.
        """
        raise NotImplementedError('`get_primary_type()` must be implemented.')

    def get_subtypes(self):
        """
        Returns the subtype names accepted by this view, mapped to their
        `subtype` descriptors.
        """
        subtypes = OrderedDict()

        for subtype in self.subtypes or []:
            subtype.viewset.request = self.request
            subtypes[subtype.type] = subtype

        return subtypes

    def get_relationships(self):
        """
        Returns the relationship names associated with this view, mapped to
        their `rel` descriptors.
        """
        rels = OrderedDict()

        for rel in self.relationships or []:
            rel.viewset.request = self.request
            rels[rel.relname] = rel

        return rels

    def get_basename(self):
        """
        The `basename` to use for reversing URLs. You may need to override
        this if you provide a base_name to your router.
        """
        # TODO: make less meh?
        self.__router = getattr(self, '__router', routers.BaseAPIRouter())
        return self.__router.get_default_base_name(self)

    def _get_dynamic_views(self):
        detail_views = []
        list_views = []
        for methodname in dir(self.__class__):
            attr = getattr(self.__class__, methodname)
            kwargs = getattr(attr, 'kwargs', None)
            httpmethods = getattr(attr, 'bind_to_methods', None)
            detail = getattr(attr, 'detail', True)
            if httpmethods:
                url_path = kwargs.get('url_path', None) or methodname
                if detail:
                    detail_views.append(url_path.replace('_', '-'))
                else:
                    list_views.append(url_path.replace('_', '-'))

        return detail_views, list_views

    def get_resource_actions(self, resource_id):
        """
        Returns a dictionary of {urlname: url} for a resource's action routes.
        These routes are dynamically generated using the @detail_route
        decorator on view methods.
        """
        base_name = self.get_basename()
        view_names = self._get_dynamic_views()[0]

        return OrderedDict(((
            view_name, reverse("%s-%s" % (base_name, view_name), self.request, args=[resource_id])
        ) for view_name in view_names))

    def get_collection_actions(self):
        """
        Returns a dictionary of {urlname: url} for a collection's action
        routes. These routes are dynamically generated using the @list_route
        decorator on view methods.
        """
        base_name = self.get_basename()
        view_names = self._get_dynamic_views()[1]

        return OrderedDict(((
            view_name, reverse("%s-%s" % (base_name, view_name), self.request)
        ) for view_name in view_names))

    # Document validation

    def get_data(self, document):
        """
        Get the primary 'data' from the request document.
        """
        try:
            return document['data']
        except KeyError:
            raise exceptions.MalformedDocument('data', '/data')

    def get_reldata(self, document, relname):
        """
        Get the related 'data' from the request document.
        """
        # TODO: This should parse from the full document
        try:
            return document['data']
        except KeyError:
            raise exceptions.MalformedDocument('data', '/%s/data' % relname)

    # Identity & type validation

    def validate_identity(self, data, instance=None):
        """
        Validate the identity of the request data.
        """
        errors = self._validate_id(data, instance)
        errors += self._validate_type(data, instance)

        if errors:
            raise exceptions.ErrorList(errors)

    def _validate_id(self, data, instance=None):
        errors = []

        if not instance:
            if 'id' in data and not self.allow_client_generated_ids:
                errors.append(exceptions.PermissionDenied('Client-Generated IDs are not supported.'))

        else:
            if 'id' not in data:
                errors.append(exceptions.ParseError('Resource ID not specified.'))

            elif data['id'] != self.get_resource_id(instance):
                errors.append(exceptions.Conflict('Resource ID mismatch.'))

        return errors

    def _validate_type(self, data, instance=None):
        errors = []

        if 'type' not in data:
            errors.append(exceptions.ParseError('Resource type not specified.'))

        if not (data['type'] == self.get_primary_type() or data['type'] in self.get_subtypes()):
            raise exceptions.Conflict('Resource type not accepted.')

        if instance:
            if data['type'] != self.get_resource_type(instance):
                errors.append(exceptions.Conflict('Resource type mismatch.'))

        return errors

    # Response building methods

    def get_default_links(self):
        """
        The default top-level links for the current request. Contains the
        `self` link for the current request.
        This method should be overridden in order to provide addtitional
        top-level default links, such as pagination.
        """
        return OrderedDict([
            ('self', self.request.build_absolute_uri()),
        ])

    def build_response_body(self, **kwargs):
        """
        Format the top-level repsonse body.
        """
        body = OrderedDict()

        # TODO: One of the following keys is required. There should
        # probably be an internal API error that's raised.
        # if not any(key in kwargs for key in ('data', 'errors', 'meta')):
        #     raise APIErrorOrSomething() or ImproperlyConfigured()

        for key in ('jsonapi', 'links', 'data', 'included', 'errors', 'meta'):
            if key in kwargs:
                body[key] = kwargs[key]
        return body

    def get_relationship(self, relname):
        """
        Returns the relationship for a given relationship name. If no name is
        specified, it attempts to get the relationship for the current request.
        """
        relationships = self.get_relationships()
        if relname in relationships:
            return relationships[relname]

        # raise 404 if no relationship was found. This also covers '/relationships'?
        raise exceptions.RelationshipNotFound(relname)

    # Resource building methods

    def get_resource(self):
        raise NotImplementedError('`get_resource()` must be implemented.')

    def get_resource_id(self, instance):
        raise NotImplementedError('`get_resource_id()` must be implemented.')

    def get_resource_type(self, instance):
        raise NotImplementedError('`get_resource_type()` must be implemented.')

    def get_resource_attributes(self, instance):
        raise NotImplementedError('`get_resource_attributes()` must be implemented.')

    def get_resource_relationships(self, instance):
        raise NotImplementedError('`get_resource_relationships()` must be implemented.')

    def get_resource_links(self, instance):
        raise NotImplementedError('`get_resource_links()` must be implemented.')

    def get_resource_meta(self, instance):
        return None

    def build_resource(self, instance, linkages=None):
        """
        Returns a 'resource object' for a resource instance, in conformance with:
        http://jsonapi.org/format/#document-resource-objects
        """
        subtype = self.get_resource_type(instance)
        subtype = self.get_subtypes().get(subtype)
        if subtype is not None:
            return subtype.viewset.build_resource(instance, linkages)

        data = OrderedDict((
            ('id', self.get_resource_id(instance)),
            ('type', self.get_resource_type(instance)),
            ('links', self.get_resource_links(instance)),
            ('attributes', self.get_resource_attributes(instance)),
            ('relationships', self.get_resource_relationships(instance, linkages)),
            ('meta', self.get_resource_meta(instance)),
        ))

        # filter out empty values
        return OrderedDict((k, v) for k, v in list(data.items()) if v)

    def build_resource_identifier(self, instance):
        """
        Returns a 'resource identifier object' for a resource instance, in conformance with:
        http://jsonapi.org/format/#document-resource-identifier-objects
        """
        subtype = self.get_resource_type(instance)
        subview = self.get_subtypes().get(subtype)
        if subview is not None:
            return subview.build_resource_identifier(instance)

        data = OrderedDict((
            ('id', self.get_resource_id(instance)),
            ('type', self.get_resource_type(instance)),
            ('meta', self.get_resource_meta(instance)),
        ))

        # filter out empty values
        return OrderedDict((k, v) for k, v in list(data.items()) if v)

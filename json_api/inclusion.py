
from collections import OrderedDict, Iterable
from django.utils import six
from json_api.exceptions import ErrorList, NotFound, ParseError
from json_api.settings import api_settings
from json_api.utils import view_meta

# TODO: could probably use a rewrite, but is a good first pass.



# Inclusion is similar to pagination in that it modifies both the queryset as well
# as the response data. pagination provides `paginate_queryset` as well as
# `get_paginated_response` methods.

# Inclusion is similar. It should have a method for potentially modifying the queryset
# and a method for altering the response data.

# note that the queryset modification ties pagination/inclusion to the generic view
# implementations, as they are both reliant on Django's ORM.
# - The generic view provides a `paginator` hook for resolving the `pagination_class`
#   into the actual paginator instance.
# - The generic view provides a `paginate_queryset` and `get_paginated_response`
#   methods which proxy the actual implementation of the paginator.

# get_paginated_response is an incorrect optimization, as the paginator knows too
# little about json-api to construct a well formed, paginated response.

# The problem with the inclusion implementation is that we cannot mimic
# paginate_queryset. This method returns a list of objects instead of a queryset, so
# queryset modification ends here.


class BaseInclusion(object):

    def get_include_paths(self, queryset, request, view=None):  # pragma: no cover
        raise NotImplementedError('get_include_paths() must be implemented.')

    def get_included_data(self, data, paths):  # pragma: no cover
        raise NotImplementedError('get_included_data() must be implemented.')


class RelatedResourceInclusion(BaseInclusion):
    """
    An inclusion implementation that uses related resource views to determine path
    validity and render the associated resource objects.

    Related resource inclusion is controlled through the `include_rels` attribute. It
    accepts a list of `relname`s or the special keyword '__all__'. Includable rels can
    be disabled by setting the value to None.

    You can set the default included relationships with the `includes` attribute on the
    view class. This accepts a list of relationship paths.

    ex::

        class PersonViewSet(viewsets.ResourceViewSet):
            ...
            rels = [
                rel('articles', 'ArticleViewSet', 'article')
            ]

        class ArticleViewSet(viewsets.ResourceViewSet):
            ...
            include_rels = ['author']
            rels = [
                rel('author', 'PersonViewSet')
            ]

        class CommentViewSet(viewsets.ResourceViewSet):
            ...
            include_rels = ['article',]
            include = ['article', 'article.author']
            rels = [
                rel('article', 'ArticleViewSet')
            ]

    The comment resource would include the article and article author by default.

    """
    include_param = 'include'
    include_delimiter = api_settings.PATH_DELIMITER
    include_rels = None

    def get_include_paths(self, queryset, request, view=None):
        """
        Returns the related inclusion paths for the requested data.

        Included relationships are set by a comma delimited ?include=... query
        parameter.
        """
        params = request.query_params.get(self.include_param)
        if params:
            paths = [param.strip() for param in params.split(',')]

            self.check_include_paths(queryset, paths, view)
            return paths

        # No paths were included, use defaults
        return self.get_default_include_paths(view)

    def get_default_include_paths(self, view):
        # An endpoint MAY return resources related to the primary data by default.
        include = getattr(view, 'include', None)
        if isinstance(include, six.string_types):
            return (include,)
        return include

    def check_include_paths(self, queryset, paths, view):
        invalid_paths = [p for p in paths if self.is_invalid_include(p, view)]

        if invalid_paths:
            raise ErrorList(errors=[
                ParseError(
                    detail='`%s` is not a valid include path.' % f,
                    source={'parameter': self.include_param}
                ) for f in invalid_paths
            ])

    def is_invalid_include(self, path, view):
        """
        Determines if an include path is valid for a view. A view specifies which of its
        relationships are includable. A path is determined to be valid if each subsequent
        part of the path is allowed to be included by its corresponding view.

        Reference:
        http://jsonapi.org/format/#document-resource-object-fields

        """
        valid_rels = self.get_includable_rels(view)

        # print valid_rels

        # determine if this is a relationship path or an attribute
        try:
            rel, related = path.split(self.include_delimiter, 1)
        except ValueError:
            rel, related = path, None

        # only check for relationship if we're attempting a related include
        if related:
            try:
                rel = view.get_relationship(rel)
            except NotFound:
                # since the field is valid, this implies that a related lookup
                # was attempted on a resource attributes
                return True
            else:
                return self.is_invalid_include(related, rel.viewset)

        # ensure fields is within set of all valid fields
        return rel not in valid_rels

    def get_includable_rels(self, view):
        """
        Returns the set of fields for a resource view that are able to be included.

        Reference:
        http://jsonapi.org/format/#document-resource-object-fields

        """
        include_rels = getattr(view, 'include_rels', self.include_rels)
        all_rels = view_meta.get_rel_attnames(view).keys()

        if include_rels is None:
            include_rels = []

        elif include_rels == '__all__':
            include_rels = all_rels

        # ensure that the valid include fields are within the set of all relationships
        assert set(include_rels).issubset(set(all_rels)), \
            "'%s.include_rels' must be valid resource relnames. Valid relnames: %s" % \
            (view.__class__.__name__, all_rels)

        return include_rels

    def aggregate_rels(self, paths):
        """
        Covert a map of related paths into a dictionary or {rels: [subpaths]}

        ex::

            ['a.a', 'a.b', 'a.c', 'b', b.a']
            into
            {'a': ['a', 'b', 'c'], 'b': ['a']}

        """
        rels = OrderedDict()

        for path in paths:
            parts = path.split(self.include_delimiter, 1)
            rel = parts[0]
            subpath = parts[1:]  # list of one paths

            rels.setdefault(rel, [])
            rels[rel] += subpath

        return rels

    def get_included_data(self, data, paths, view):
        # base case - no paths, no included data
        if not paths:
            return {}

        if not isinstance(data, Iterable):
            data = [data]

        included_data = OrderedDict()

        aggregated_rels = self.aggregate_rels(paths)
        for instance in data:
            for relname, subpaths in aggregated_rels.items():
                rel = view.get_relationship(relname)

                # use the related view to access the included data.
                # this will perform permission checks, filtering, etc...
                related_data = view.get_related_data(rel, instance)
                if not isinstance(related_data, Iterable):
                    related_data = [related_data]

                # use the related view to go ahead and build the resource objects
                resource_objects = [rel.viewset.build_resource(inst) for inst in related_data]

                # covert to ordered dict of {identity: object}
                resource_objects = OrderedDict((
                    (inst['id'], inst['type'], ), inst
                ) for inst in resource_objects)

                # merge into overall included data
                included_data.update(resource_objects)

                # merge in included subpaths
                included_data.update(rel.viewset.get_included_data(related_data, subpaths))

        return included_data

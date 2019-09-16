
import re
from django.core.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework_filters import backends, filterset
from django_filters.filterset import STRICTNESS
from json_api.exceptions import ErrorList, NotFound, ParseError, FilterValidationError
from json_api.settings import api_settings
from json_api.utils import view_meta


class RelatedOrderingFilter(OrderingFilter):
    """
    Extends OrderingFilter to support ordering by fields in related resources.

    Adapated from:
    https://github.com/tomchristie/django-rest-framework/issues/1005
    """
    ordering_delimiter = api_settings.PATH_DELIMITER

    def get_ordering(self, request, queryset, view):
        ordering = super(RelatedOrderingFilter, self).get_ordering(request, queryset, view)
        if ordering:
            ordering = [self.translate_field(field, view) for field in ordering]

        return ordering

    def translate_field(self, field, view):
        """
        Translate the ordering parameter delimiter to be compatible with
        django's filtering/ordering syntax.
        """
        descending = field.startswith('-')
        field = field.lstrip('-')

        # determine if this is a relationship path or an attribute
        try:
            field, related = field.split(self.ordering_delimiter, 1)
        except ValueError:
            related = None

        if related:
            rel = view.get_relationship(field)
            related = self.translate_field(related, rel.viewset)

        if field != 'id':
            # translate from resource name to model attname.
            fields_map = view_meta.get_field_attnames(view)
            field = fields_map[field]
        else:
            field = 'pk'

        # serializer source may be '.' delimited across relationships
        field = field.replace('.', '__')

        if descending:
            field = '-%s' % field

        if related:
            return '__'.join([field, related])
        return field

    def get_ordering_fields(self, view):
        """
        Returns the set of fields for a resource view that are able to be ordered upon.

        Reference:
        http://jsonapi.org/format/#document-resource-object-fields

        """
        ordering_fields = getattr(view, 'ordering_fields', self.ordering_fields)
        all_fields = list(view_meta.get_field_attnames(view).keys())

        if ordering_fields is None:
            ordering_fields = []

        elif ordering_fields == '__all__':
            ordering_fields = all_fields

        # ensure that the valid ordering fields are within the set of all fields
        assert set(ordering_fields).issubset(set(all_fields)), \
            "'%s.ordering_fields' must be valid resource fields. Valid fields: %s" % \
            (view.__class__.__name__, all_fields)

        return ordering_fields

    def remove_invalid_fields(self, queryset, fields, view):
        invalid_fields = [field.lstrip('-') for field in fields]
        invalid_fields = [f for f in invalid_fields if self.is_invalid_field(f, view)]

        if invalid_fields:
            raise ErrorList(errors=[
                ParseError(
                    detail='`%s` is not a valid sort key.' % f,
                    source={'parameter': self.ordering_param}
                ) for f in invalid_fields
            ])

        return fields

    def is_invalid_field(self, field, view):
        """
        Determines if a field is valid for a view. If the field is a relationship
        path, then the relationship is traversed and subsequent views are checked
        for each part of the path.

        Reference:
        http://jsonapi.org/format/#document-resource-object-fields

        """
        ordering_fields = self.get_ordering_fields(view)

        # determine if this is a relationship path or an attribute
        try:
            field, related = field.split(self.ordering_delimiter, 1)
        except ValueError:
            related = None

        # only check for relationship if we're attempting a related sort
        if related:
            try:
                rel = view.get_relationship(field)
            except NotFound:
                # since the field is valid, this implies that a related lookup
                # was attempted on a resource attributes
                return True
            else:
                return self.is_invalid_field(related, rel.viewset)

        # ensure fields is within set of all valid fields
        return field not in ordering_fields


class FieldLookupFilter(backends.DjangoFilterBackend):
    """
    Wraps DRF-filters `DjangoFilterBackend` to support JSON-API compatible query string
    syntax. The filter backend is agnostic to the format of the lookup syntax, as long as
    it matches against `filter[lookup]=value`.

    ie,
        /api/books?filter[author__id__lte]=5
    """
    filter_regex = re.compile(r'^filter\[(?P<lookup>.+)\]$')

    def filter_queryset(self, request, queryset, view):
        filter_class = self.get_filter_class(view, queryset)
        filter_regex = self.filter_regex

        filters = {filter_regex.match(p): v for p, v in list(request.query_params.items())}
        filters = {p.group('lookup'): v for p, v in list(filters.items()) if p is not None}

        if filter_class:
            if hasattr(filter_class, 'get_subset'):
                filter_class = filter_class.get_subset(filters)

            try:
                return filter_class(filters, queryset=queryset).qs
            except ValidationError as e:
                raise self._convert_exception(e)

        return queryset

    def _convert_exception(self, exc):
        errors = []

        for param, exc_list in list(exc.message_dict.items()):
            parameter = 'filter[%s]' % param
            errors += [FilterValidationError(detail, parameter) for detail in exc_list]

        return ErrorList(errors)


class FilterSet(filterset.FilterSet):
    strict = STRICTNESS.RAISE_VALIDATION_ERROR

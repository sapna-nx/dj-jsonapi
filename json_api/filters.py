
from django.core.exceptions import ImproperlyConfigured
from rest_framework.filters import OrderingFilter
from rest_framework.utils import model_meta
from json_api.exceptions import ParseError
from json_api.settings import api_settings


class RelatedOrderingFilter(OrderingFilter):
    """
    Extends OrderingFilter to support ordering by fields in related models.

    Adapated from:
    https://github.com/tomchristie/django-rest-framework/issues/1005
    """
    ordering_delimiter = api_settings.ORDERING_DELIMITER

    def get_ordering(self, request, queryset, view):
        ordering = super(RelatedOrderingFilter, self).get_ordering(request, queryset, view)
        if ordering:
            ordering = [self.translate_field(field) for field in ordering]

        return ordering

    def translate_field(self, field):
        """
        Translate the ordering parameter delimiter to be compatible with
        django's filtering/ordering syntax.
        """
        # If our ordering delimiter is the same as django's separator, noop.
        if self.ordering_delimiter == '__':
            return field
        return field.replace(self.ordering_delimiter, '__')

    def _view_fields(self, view):
        """
        Returns the list of fields the view is aware of. This is the
        combination of its serializer's fields and its relationships.
        """
        serializer_class = view.get_serializer_class()
        relationships = view.relationships or list()

        return [
            field_obj.source or field_name
            for field_name, field_obj in serializer_class().fields.items()
            if not getattr(field_obj, 'write_only', False)
        ] + [rel['accessor_name'] for rel in relationships]

    def remove_invalid_fields(self, queryset, fields, view):
        valid_fields = getattr(view, 'ordering_fields', self.ordering_fields)

        # If `valid_fields` are not provided, we need to check that the field
        # is defined in either the view's serializer or relationships.
        # Note that we can only check by traversing the relations/fields.
        # Building a complete list of valid fields is not possible due to
        # possible reference cycles between relationships.

        # TODO:
        # Raise a JSON-API exception.
        for field in fields:
            field = field.lstrip('-')
            if valid_fields is None:
                if not self.is_valid_field(queryset, field, view):
                    raise ParseError('`%s` is not a valid sort key.' % field)
            else:
                if field not in valid_fields:
                    raise ParseError('`%s` is not a valid sort key.' % field)

        return fields

    def is_valid_field(self, queryset, field, view):
        """
        Return true if the field exists within the model (or in the related
        model specified using the Django ORM __ notation), and if the field
        or relationship is defined within the view.
        """
        # ensure the view is properly defined with serializer.
        serializer_class = view.get_serializer_class()
        if serializer_class is None:
            msg = ("Cannot use %s on a view which does not have either a "
                   "'serializer_class' or 'ordering_fields' attribute.")
            raise ImproperlyConfigured(msg % self.__class__.__name__)

        info = model_meta.get_field_info(serializer_class.Meta.model)

        # determine if this is a relationship or a field ordering
        try:
            field, related = field.split(self.ordering_delimiter, 1)
        except ValueError:
            related = None

        # handle related ordering. Note that this does not handle ordering
        # on relationships that don't have a related sub-ordering.
        # i.e., handles `user.name`, not `user`
        if related:
            # only check for relationship if we're attempting a related sort
            if getattr(view, 'relationships', None) is None:
                msg = ("Cannot use %s on a view which does not have either a "
                       "'relationships' or 'ordering_fields' attribute.")
                raise ImproperlyConfigured(msg % self.__class__.__name__)

            rel = view.get_relationship(field)

            # relationshhip must both be defined on the model and the view
            if not rel or field not in info.relations:
                return False

            related_view = view.get_viewset(rel)()
            return self.is_valid_field(queryset, related, related_view)

        # handle field ordering
        else:
            # ensure that the view is aware of the sort key
            if field not in self._view_fields(view):
                return False

            # also ensure that the field exists on the model or as an
            # aggregation key
            valid_fields = info.fields.keys() + info.relations.keys()
            if queryset.model == serializer_class.Meta.model:
                valid_fields += queryset.query.aggregates.keys()

            return field in valid_fields

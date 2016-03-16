
from collections import OrderedDict
from django.core.exceptions import ImproperlyConfigured


def get_attribute_attnames(view):
    """
    Return a map of {resource attribute name: model attname} for a view.
    """
    serializer_class = getattr(view, 'serializer_class')
    if serializer_class is None:
        raise ImproperlyConfigured(
            "Cannot use 'get_attribute_attnames' on a view which "
            "does not have a 'serializer_class'."
        )

    return OrderedDict(
        (field_name, field.source)
        for field_name, field in serializer_class().fields.items()
        if not getattr(field, 'write_only', False)
    )


def get_rel_attnames(view):
    """
    Return a map of {resource rel name: model attname} for a view.
    """
    if view.relationships is None:
        return OrderedDict()
    return OrderedDict((rel.relname, rel.attname) for rel in view.relationships)


def get_field_attnames(view):
    """
    Return a map of {resource field name: model attname} for a view.
    """
    fields_map = get_attribute_attnames(view)
    fields_map.update(get_rel_attnames(view))
    return fields_map

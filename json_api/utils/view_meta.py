
from django.core.exceptions import ImproperlyConfigured


def get_field_attnames(view):
    """
    Return a map of {resource field: model attname} for a view.
    """
    serializer_class = getattr(view, 'serializer_class')
    if serializer_class is None:
        raise ImproperlyConfigured(
            "Cannot use 'get_field_attnames' on a view which "
            "does not have a 'serializer_class'."
        )

    field_map = {
        field_name: field.source
        for field_name, field in serializer_class().fields.items()
        if not getattr(field, 'write_only', False)
    }

    if hasattr(view, 'relationships'):
        field_map.update({
            rel.relname: rel.attname for rel in view.relationships
        })

    return field_map

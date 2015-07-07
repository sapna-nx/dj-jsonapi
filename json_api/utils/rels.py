
import inspect
from collections import namedtuple
from django.utils import six

from . import import_class


class rel(namedtuple('Relationship', ['attname', 'viewset', 'relname'])):
    """
    Relationship descriptor.

    *attname* Corresponds to the `name` property of a forward relation's field,
              or the `name` property of a reverse relation's ForeignObjectRel.
    *viewset* The viewset that manages the related resource collection.
    *relname* The display name for the relationship. Defaults to attname if
              not provided.

    Note:
    The `attname` attribute does not correspond to a django field's `attname`,
    per the description, however this name was chosen since it serves the same
    purpose. Also, it's seven chars in length.
    """
    def __new__(cls, attname, viewset, relname=None):

        if not relname:
            relname = attname

        return super(rel, cls).__new__(cls, attname, viewset, relname)


class resolved_rel(namedtuple('ResolvedRelationship', ['attname', 'relname', 'viewset', 'info'])):
    """
    A 'resolved' relationship descriptor that contains all of the relevant metadata
    about the relationship.

    """
    def __new__(cls, attname, relname, viewset, info, request):
        if isinstance(viewset, six.string_types):
            viewset = import_class(viewset)

        if inspect.isclass(viewset):
            viewset = viewset()

        viewset.request = request
        return super(resolved_rel, cls).__new__(cls, attname, relname, viewset, info)

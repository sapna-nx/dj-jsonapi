
import six
import inspect
from collections import namedtuple

from . import import_class


class rel(namedtuple('Relationship', ['attname', 'viewset', 'relname'])):
    """
    Relationship descriptor.

    *attname* Corresponds to the attname property of the model's related field.
    *viewset* The viewset that manages the related resource collection.
    *relname* The display name for the relationship. Defaults to attname if
              not provided.

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

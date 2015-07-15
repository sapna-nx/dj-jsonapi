
import inspect
from collections import namedtuple
from django.utils import six

from . import import_class


class rel(namedtuple('Relationship', ['relname', 'viewset', 'attname'])):
    """
    A generic relationship descriptor.

    *relname* The name of the relationship. Used during serialization.
    *viewset* The viewset that manages the related resource collection.
    *attname* The name used to access the attribute on the resource.
              Defaults to relname if not provided.

    """
    def __new__(cls, relname, viewset, attname=None):

        if attname is None:
            attname = relname

        return super(rel, cls).__new__(cls, relname, viewset, attname)


class model_rel(namedtuple('ResolvedModelRelationship', ['relname', 'attname', 'viewset', 'info'])):
    """
    A 'resolved' model relationship descriptor that contains all of the relevant metadata
    about a relationship. This descriptor should be constructed by the viewset, and
    derived from the original `rel`.

    *relname* The name of the relationship. Used during serialization.
    *attname* Reference `rel.attname`. This should correspond to the `name` property of a
              forward relation's field, or the `name` property of a reverse relation's
              ForeignObjectRel.
    *viewset* The viewset that manages the related resource collection.
    *info*    Metadata that describes the relationship.
    *request* The origin request. This is attached to the viewset after instantiation.

    """
    def __new__(cls, relname, attname, viewset, info, request):
        if isinstance(viewset, six.string_types):
            viewset = import_class(viewset)

        if inspect.isclass(viewset):
            viewset = viewset()

        viewset.request = request
        return super(model_rel, cls).__new__(cls, relname, attname, viewset, info)

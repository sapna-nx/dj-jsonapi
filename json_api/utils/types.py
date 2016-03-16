
import inspect
from django.utils import six

from . import import_class


class subtype(object):
    """
    A generic polymorphic type descriptor.

    *type* The type string used to identify the subtype.
    *viewset* The viewset that manages the subtype resource collection.

    """

    def __init__(self, viewset):
        self.viewset = viewset

    def viewset():
        def fget(self):
            viewset = self._viewset

            if isinstance(viewset, six.string_types):
                viewset = import_class(viewset)

            if inspect.isclass(viewset):
                viewset = viewset()

            self._viewset = viewset
            return self._viewset

        def fset(self, value):
            self._viewset = value

        return locals()
    viewset = property(**viewset())

    @property
    def type(self):
        return self.viewset.get_primary_type()

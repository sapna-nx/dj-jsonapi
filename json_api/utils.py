
from django.core import urlresolvers


def import_class(path):
    """
    Import a class from a dot-delimited module path. Accepts both dot and
    colon seperators for the class portion of the path.

    ex::
        import_class('package.module.ClassName')

        or

        import_class('package.module:ClassName')
    """
    if ':' in path:
        module_path, class_name = path.split(':')
    else:
        module_path, class_name = path.rsplit('.', 1)

    module = __import__(module_path, fromlist=[class_name], level=0)
    return getattr(module, class_name)


def relative_viewname(viewname, resolver):
    """
    Helper for building a fully namespaced `viewname` given a URL resolver.
    (This is typically from the current request.)
    """
    return ':'.join(
        filter(None, [
            resolver.app_name, resolver.namespace, viewname
        ])
    )


def reverse(viewname, request, urlconf=None, args=None, kwargs=None, current_app=None):
    """
    A wrapper around Django's builtin `django.core.urlresolvers.reverse` utility function
    that will use the current request to derive the `app_name` and `namespace`. This is
    most useful for apps that need to reverse their own URLs. Additionally, it uses the
    current request to build an absolute uri suitable for API usage.
    """
    viewname = relative_viewname(viewname, request.resolver_match)
    relative_url = urlresolvers.reverse(viewname, urlconf, args, kwargs, current_app)
    return request.build_absolute_uri(relative_url)

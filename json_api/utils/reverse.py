
from django.urls import reverse as rev


def relative_viewname(viewname, resolver):
    """
    Helper for building a fully namespaced `viewname` given a URL resolver.
    (This is typically from the current request.)
    """
    if resolver is None:
        return viewname

    return ':'.join(
        [_f for _f in [
            resolver.app_name, viewname
        ] if _f]
    )


def reverse(viewname, request, urlconf=None, args=None, kwargs=None, current_app=None):
    """
    A wrapper around Django's builtin `django.urls.reverse` utility function
    that will use the current request to derive the `app_name` and `namespace`. This is
    most useful for apps that need to reverse their own URLs. Additionally, it uses the
    current request to build an absolute uri suitable for API usage.
    """
    # print(">>>>>>>>>>>>>>>>>>>>>>", viewname, request, urlconf, args, kwargs, current_app)
    viewname = relative_viewname(viewname, request.resolver_match)
    # print("<<<<<<<<<<<<<<<<<<<<<<<<<", viewname, urlconf, args, kwargs, current_app)
    relative_url = rev(viewname, urlconf, args, kwargs, current_app)
    # print("::::::::::::::", relative_url)

    return request.build_absolute_uri(relative_url)

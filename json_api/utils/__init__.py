
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
        module_path, class_name = str(path).split(':')
    else:
        module_path, class_name = str(path).rsplit('.', 1)

    module = __import__(module_path, fromlist=[class_name], level=0)
    return getattr(module, class_name)

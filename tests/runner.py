import os
import sys
import glob
import django

base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
eggs = os.path.abspath(os.path.join(base, "*.egg"))

sys.path += glob.glob(eggs)
sys.path.append(base)

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'


def main():
    """
    Test handler code based on Django's 'test' command:
    https://github.com/django/django/blob/1.8/django/core/management/commands/test.py#L79
    """
    from django.conf import settings
    from django.test import utils

    try:
        # https://docs.djangoproject.com/en/1.8/releases/1.7/#app-loading-changes
        django.setup()
    except:
        pass

    TestRunner = utils.get_runner(settings)
    test_runner = TestRunner()

    test_module_name = 'tests'

    failures = test_runner.run_tests([test_module_name])

    if failures:
        sys.exit(bool(failures))


if __name__ == '__main__':
    main()

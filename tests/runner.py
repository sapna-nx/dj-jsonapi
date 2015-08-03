import os
import sys
import glob

base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
eggs = os.path.abspath(os.path.join(base, "*.egg"))

sys.path += glob.glob(eggs)
sys.path.append(base)

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'


def main(argv):
    from django.core.management import execute_from_command_line
    execute_from_command_line(argv)


if __name__ == '__main__':
    args = sys.argv
    args.insert(1, 'test')
    main(args)

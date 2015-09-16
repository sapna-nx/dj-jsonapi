import os
from setuptools import setup, find_packages
from setuptools.command.test import test

README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


class Test(test):
    user_options = [
        ('test-labels=', 'l', "Test labels to pass to runner.py test"),
        ('djtest-args=', 'a', "Arguments to pass to runner.py test"),
    ]

    def initialize_options(self):
        test.initialize_options(self)
        self.test_labels = 'tests'
        self.djtest_args = ''

    def finalize_options(self):
        test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        from tests.runner import main

        test_labels = self.test_labels.split()
        djtest_args = self.djtest_args.split()
        main(['runner.py', 'test'] + test_labels + djtest_args)


setup(
    name='dj-jsonapi',
    version='0.0.1',
    license='BSD License',

    description='A JSON-API server implementation built for Django on top of Django Rest Framework',
    long_description=README,
    url='https://github.com/ITNG/dj-jsonapi',
    author='Ryan P Kilby',
    author_email='rpkilby@ncsu.edu',
    install_requires=['django', 'djangorestframework>=3.2,!=3.2.3,', 'djangorestframework-filters'],
    packages=find_packages(exclude=('tests', )),

    tests_require=['fantasy-database'],

    cmdclass={
        'test': Test,
    },

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)

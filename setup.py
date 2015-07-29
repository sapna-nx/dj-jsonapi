import os
from setuptools import setup, find_packages

README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='dj-jsonapi',
    version='0.0.1',
    license='BSD License',

    description='A JSON-API server implementation built for Django on top of Django Rest Framework',
    long_description=README,
    url='https://github.com/ITNG/dj-jsonapi',
    author='Ryan P Kilby',
    author_email='rpkilby@ncsu.edu',
    install_requires=['djangorestframework>=3', ],
    tests_require=['django', 'djangorestframework>=3', 'requests', ],
    test_suite='tests.runner.main',
    packages=find_packages(exclude=('tests', )),

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

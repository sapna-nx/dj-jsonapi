
# fantasy

A test app that that provides a JSON-API implementation of [endpoints/fantasy-database](https://github.com/endpoints/fantasy-database).

The `testserver` command has been overridden to download and install the fantasy-database test data.

Example usage:

In your `settings.py` module:

```python

# Testing
TESTING = len(sys.argv) > 1 and sys.argv[1] in ('test', 'testserver')

if TESTING:
    # eventually, fantasy should be moved out of this project
    INSTALLED_APPS += (
        'json_api.fantasy',
    )

...
```

In `urls.py`:
```python
from django.conf import settings
...

if settings.TESTING:
    urlpatterns += [
        url(r'^test-api/', include('json_api.fantasy.urls', namespace='test-api'),),
    ]

```
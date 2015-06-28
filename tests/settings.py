
SECRET_KEY = 'not-so-secret'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
}

INSTALLED_APPS = (
    'json_api',
    'tests',
)

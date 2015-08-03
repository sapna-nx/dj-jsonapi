
SECRET_KEY = 'not-so-secret'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    # 'django_fantasy',
    # 'json_api.fantasy',
    'tests',
)


ROOT_URLCONF = 'tests.urls'

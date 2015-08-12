
from django.conf.urls import include, url


urlpatterns = [
    url(r'^', include('json_api.fantasy.urls')),
]

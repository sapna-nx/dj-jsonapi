
from json_api.serializers import ResourceSerializer

from tests import models


class AuthorSerializer(ResourceSerializer):
    class Meta:
        model = models.Author


class CoverSerializer(ResourceSerializer):
    class Meta:
        model = models.Cover


class TagSerializer(ResourceSerializer):
    class Meta:
        model = models.Tag


class BookSerializer(ResourceSerializer):
    class Meta:
        model = models.Book

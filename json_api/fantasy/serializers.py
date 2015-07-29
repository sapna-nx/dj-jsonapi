
from json_api.serializers import ResourceSerializer
from json_api.fantasy import models


class AuthorSerializer(ResourceSerializer):
    class Meta:
        model = models.Author


class SeriesSerializer(ResourceSerializer):
    class Meta:
        model = models.Series


class BookSerializer(ResourceSerializer):
    class Meta:
        model = models.Book


class ChapterSerializer(ResourceSerializer):
    class Meta:
        model = models.Chapter


class StoreSerializer(ResourceSerializer):
    class Meta:
        model = models.Store


class PhotoSerializer(ResourceSerializer):
    class Meta:
        model = models.Photo


from json_api import viewsets
from json_api.utils.rels import rel

from json_api.fantasy import models, serializers


class AuthorView(viewsets.ResourceViewSet):
    queryset = models.Author.objects.all()
    serializer_class = serializers.AuthorSerializer
    include_rels = '__all__'

    relationships = (
        rel('books', 'json_api.fantasy.views.BookView', 'book'),
    )


class SeriesView(viewsets.ResourceViewSet):
    queryset = models.Series.objects.all()
    serializer_class = serializers.SeriesSerializer
    include_rels = '__all__'

    relationships = (
        rel('books', 'json_api.fantasy.views.BookView', 'book'),
        rel('photo', 'json_api.fantasy.views.PhotoView'),
    )


class BookView(viewsets.ResourceViewSet):
    queryset = models.Book.objects.all()
    serializer_class = serializers.BookSerializer
    include_rels = '__all__'

    relationships = (
        rel('series', 'json_api.fantasy.views.SeriesView'),
        rel('author', 'json_api.fantasy.views.AuthorView'),
        rel('chapters', 'json_api.fantasy.views.ChapterView', 'chapter'),
        rel('stores', 'json_api.fantasy.views.StoreView', 'store'),
    )


class ChapterView(viewsets.ResourceViewSet):
    queryset = models.Chapter.objects.all()
    serializer_class = serializers.ChapterSerializer
    include_rels = '__all__'
    ordering = ('book', 'ordering')

    relationships = (
        rel('book', 'json_api.fantasy.views.BookView'),
    )


class StoreView(viewsets.ResourceViewSet):
    queryset = models.Store.objects.all()
    serializer_class = serializers.StoreSerializer
    include_rels = '__all__'

    relationships = (
        rel('books', 'json_api.fantasy.views.BookView'),
    )


class PhotoView(viewsets.ResourceViewSet):
    queryset = models.Photo.objects.all()
    serializer_class = serializers.PhotoSerializer


from json_api.utils.rels import rel
from json_api import generics

from tests import models, serializers


class AuthorView(generics.GenericResourceView):
    queryset = models.Author.objects.all()
    serializer_class = serializers.AuthorSerializer
    ordering_fields = '__all__'

    relationships = [rel('books', 'tests.views.BookView', 'book'), ]


class CoverView(generics.GenericResourceView):
    queryset = models.Cover.objects.all()
    serializer_class = serializers.CoverSerializer
    ordering_fields = '__all__'

    relationships = [rel('book', 'tests.views.BookView'), ]


class TagView(generics.GenericResourceView):
    queryset = models.Tag.objects.all()
    serializer_class = serializers.TagSerializer
    ordering_fields = '__all__'

    relationships = [rel('books', 'tests.views.BookView', 'book'), ]


class BookView(generics.GenericResourceView):
    queryset = models.Book.objects.all()
    serializer_class = serializers.BookSerializer
    ordering_fields = '__all__'

    relationships = [
        rel('author', 'tests.views.AuthorView'),
        rel('cover', 'tests.views.CoverView'),
        rel('tags', 'tests.views.TagView'),
    ]

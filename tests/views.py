
from json_api.utils.rels import rel
from json_api import generics, mixins

from tests import models, serializers


class ListMixin(mixins.ListResourceMixin):
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_resource_links(self, *args, **kwargs):
        return {}

    def get_relationship_links(self, *args, **kwargs):
        return {}


class DetailMixin(mixins.RetrieveResourceMixin):
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def get_resource_links(self, *args, **kwargs):
        return {}

    def get_relationship_links(self, *args, **kwargs):
        return {}


class AuthorView(generics.GenericResourceView):
    queryset = models.Author.objects.all()
    serializer_class = serializers.AuthorSerializer

    relationships = [rel('books', 'tests.views.BookView', 'book'), ]


class CoverView(generics.GenericResourceView):
    queryset = models.Cover.objects.all()
    serializer_class = serializers.CoverSerializer

    relationships = [rel('book', 'tests.views.BookView'), ]


class TagView(generics.GenericResourceView):
    queryset = models.Tag.objects.all()
    serializer_class = serializers.TagSerializer

    relationships = [rel('books', 'tests.views.BookView', 'book'), ]


class BookView(generics.GenericResourceView):
    queryset = models.Book.objects.all()
    serializer_class = serializers.BookSerializer

    relationships = [
        rel('author', 'tests.views.AuthorView'),
        rel('cover', 'tests.views.CoverView'),
        rel('tags', 'tests.views.TagView'),
    ]


class PersonView(generics.GenericResourceView):
    queryset = models.Person.objects.all()
    serializer_class = serializers.PersonSerializer

    relationships = [
        rel('articles', 'tests.views.ArticleView', 'article'),
    ]


class ArticleView(generics.GenericResourceView):
    queryset = models.Article.objects.all()
    serializer_class = serializers.ArticleSerializer

    relationships = [
        rel('author', 'tests.views.AuthorView'),
        rel('comments', 'tests.views.CommentView', 'comment'),
    ]


class CommentView(generics.GenericResourceView):
    queryset = models.Comment.objects.all()
    serializer_class = serializers.CommentSerializer

    relationships = [
        rel('author', 'tests.views.AuthorView'),
        rel('article', 'tests.views.ArticleView'),
    ]

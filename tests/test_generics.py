
from django.test import TestCase
from json_api import serializers, generics
from json_api.utils.rels import rel

from tests import models


# forward/reverse relationship testing serializers
class AuthorSerializer(serializers.ResourceSerializer):
    class Meta:
        model = models.Author


class CoverSerializer(serializers.ResourceSerializer):
    class Meta:
        model = models.Cover


class TagSerializer(serializers.ResourceSerializer):
    class Meta:
        model = models.Tag


class BookSerializer(serializers.ResourceSerializer):
    class Meta:
        model = models.Book


# forward/reverse relationship testing generic views
class AuthorView(generics.GenericResourceView):
    queryset = models.Author.objects.all()
    serializer_class = AuthorSerializer

    relationships = [rel('books', 'tests.test_generics.BookView', 'book'), ]


class CoverView(generics.GenericResourceView):
    queryset = models.Cover.objects.all()
    serializer_class = CoverSerializer

    relationships = [rel('book', 'tests.test_generics.BookView'), ]


class TagView(generics.GenericResourceView):
    queryset = models.Tag.objects.all()
    serializer_class = TagSerializer

    relationships = [rel('books', 'tests.test_generics.BookView', 'book'), ]


class BookView(generics.GenericResourceView):
    queryset = models.Book.objects.all()
    serializer_class = BookSerializer

    relationships = [
        rel('author', 'tests.test_generics.AuthorView'),
        rel('cover', 'tests.test_generics.CoverView'),
        rel('tags', 'tests.test_generics.TagView'),
    ]


class TestGetRelatedData(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.author = models.Author.objects.create(name="Some author")
        cls.cover = models.Cover.objects.create(text="Some cover text")
        cls.tags = [
            models.Tag.objects.create(text="tag a"),
            models.Tag.objects.create(text="tag b"),
            models.Tag.objects.create(text="tag c"),
            models.Tag.objects.create(text="tag d"),
        ]
        cls.book = models.Book.objects.create(
            author=cls.author,
            cover=cls.cover,
            title="Some book",
        )
        cls.book.tags.add(*cls.tags)

    def test_request_attribute(self):

        view = BookView()
        try:
            view.request
        except AttributeError:
            # It currently does not matter whether the request is `None`
            # or an actual request object.
            self.fail(
                "`get_related_data()` calls `check_object_permissions()`, "
                "requiring that the view has the `request` attribute set."
            )

    def test_forwards_to_one(self):
        view = BookView()
        instance = self.book

        rel = view.get_relationship('author')
        author = view.get_related_data(rel, instance)
        self.assertEqual(author.pk, self.author.pk)
        self.assertEqual(author.name, self.author.name)

        rel = view.get_relationship('cover')
        cover = view.get_related_data(rel, self.book)
        self.assertEqual(cover.pk, self.cover.pk)
        self.assertEqual(cover.text, self.cover.text)

    def test_reverse_to_one(self):
        view = CoverView()
        instance = self.cover

        rel = view.get_relationship('book')
        book = view.get_related_data(rel, instance)
        self.assertEqual(book.pk, self.book.pk)
        self.assertEqual(book.title, self.book.title)

    def test_forwards_to_many(self):
        view = BookView()
        instance = self.book

        rel = view.get_relationship('tags')
        tags = view.get_related_data(rel, instance)

        for actual, expected in zip(tags, self.tags):
            self.assertEqual(actual.pk, expected.pk)
            self.assertEqual(actual.text, expected.text)

    def test_reverse_to_many(self):
        # reverse FK
        view = AuthorView()
        instance = self.author

        rel = view.get_relationship('books')
        books = view.get_related_data(rel, instance)
        self.assertEqual(books[0].pk, self.book.pk)
        self.assertEqual(books[0].title, self.book.title)

        # reverse m2m
        view = TagView()

        for instance in self.tags:
            rel = view.get_relationship('books')
            books = view.get_related_data(rel, instance)
            self.assertEqual(books[0].pk, self.book.pk)
            self.assertEqual(books[0].title, self.book.title)

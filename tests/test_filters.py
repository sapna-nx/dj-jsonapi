
from unittest import TestCase as UTestCase
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework import serializers
from json_api import filters
from json_api.utils.rels import rel

from tests import views, models

factory = APIRequestFactory()


# forward/reverse relationship testing generic views
class AuthorView(views.ListMixin, views.AuthorView):
    filter_backends = (filters.RelatedOrderingFilter, filters.FieldLookupFilter, )
    ordering_fields = '__all__'

    relationships = [rel('books', 'tests.test_filters.BookView', 'book'), ]


class CoverView(views.ListMixin, views.CoverView):
    filter_backends = (filters.RelatedOrderingFilter, filters.FieldLookupFilter, )
    ordering_fields = '__all__'

    relationships = [rel('book', 'tests.test_filters.BookView'), ]


class TagView(views.ListMixin, views.TagView):
    filter_backends = (filters.RelatedOrderingFilter, filters.FieldLookupFilter, )
    ordering_fields = '__all__'

    relationships = [rel('books', 'tests.test_filters.BookView', 'book'), ]


class BookView(views.ListMixin, views.BookView):
    filter_backends = (filters.RelatedOrderingFilter, filters.FieldLookupFilter, )
    ordering_fields = '__all__'

    relationships = [
        rel('author', 'tests.test_filters.AuthorView'),
        rel('cover', 'tests.test_filters.CoverView'),
        rel('tags', 'tests.test_filters.TagView'),
    ]


class RelatedOrderingFilterTests(UTestCase):

    def setUp(self):
        self.filter = filters.RelatedOrderingFilter()

    def test_translate_field(self):
        class _AuthorView(AuthorView):
            ordering_fields = '__all__'

        class _BookView(BookView):
            ordering_fields = '__all__'
            relationships = [rel('author', _AuthorView), ]

        view = BookView()

        self.assertEqual(self.filter.translate_field('id', view), 'pk')
        self.assertEqual(self.filter.translate_field('author', view), 'author')
        self.assertEqual(self.filter.translate_field('-author', view), '-author')
        self.assertEqual(self.filter.translate_field('author.name', view), 'author__name')
        self.assertEqual(self.filter.translate_field('-author.name', view), '-author__name')

    def test_translate_field_altnames(self):
        BookSerializer = BookView.serializer_class

        class AltBookSerializer(BookSerializer):
            alt_title = serializers.CharField(source='title')

            class Meta(BookSerializer.Meta):
                fields = ['alt_title', ]

        class AltBookView(BookView):
            serializer_class = AltBookSerializer

            relationships = [
                rel('alt_author', AuthorView, 'author'),
            ]

        view = AltBookView()
        self.assertEqual(self.filter.translate_field('alt_title', view), 'title')
        self.assertEqual(self.filter.translate_field('-alt_author', view), '-author')

    def test_get_ordering_fields(self):
        class NoDefinedFields(BookView):
            ordering_fields = None

        class AllFields(BookView):
            ordering_fields = '__all__'

        class FieldSubset(BookView):
            ordering_fields = ['author', 'title']

        class InvalidFields(BookView):
            ordering_fields = ['foo', 'bar']

        view = NoDefinedFields()
        self.assertEqual(self.filter.get_ordering_fields(view), [])

        view = AllFields()
        self.assertSequenceEqual(
            self.filter.get_ordering_fields(view),
            ['title', 'author', 'cover', 'tags']
        )

        view = FieldSubset()
        self.assertSequenceEqual(
            self.filter.get_ordering_fields(view),
            ['author', 'title']
        )

        view = InvalidFields()
        with self.assertRaisesRegexp(AssertionError, 'must be valid resource fields'):
            self.filter.get_ordering_fields(view)

    def test_is_invalid_field(self):
        class NoDefinedFields(BookView):
            ordering_fields = None

        class AllFields(BookView):
            ordering_fields = '__all__'

        class FieldSubset(BookView):
            ordering_fields = ['author', 'title']

        view = NoDefinedFields()
        self.assertTrue(self.filter.is_invalid_field('author', view))
        self.assertTrue(self.filter.is_invalid_field('title', view))

        view = AllFields()
        self.assertFalse(self.filter.is_invalid_field('author', view))
        self.assertFalse(self.filter.is_invalid_field('title', view))

        view = FieldSubset()
        self.assertFalse(self.filter.is_invalid_field('author', view))
        self.assertFalse(self.filter.is_invalid_field('title', view))
        self.assertTrue(self.filter.is_invalid_field('cover', view))
        self.assertTrue(self.filter.is_invalid_field('tags', view))

    def test_is_invalid_field_for_related(self):
        class NoDefinedFields(AuthorView):
            ordering_fields = None

        class AllFields(AuthorView):
            ordering_fields = '__all__'

        # Invalid author attribute lookup
        class _BookView(BookView):
            ordering_fields = '__all__'
            relationships = [rel('author', NoDefinedFields), ]

        view = _BookView()
        self.assertFalse(self.filter.is_invalid_field('author', view))
        self.assertTrue(self.filter.is_invalid_field('author.name', view))

        # Valid author attribute lookup
        class _BookView(BookView):
            ordering_fields = '__all__'
            relationships = [rel('author', AllFields), ]

        view = _BookView()
        self.assertFalse(self.filter.is_invalid_field('author', view))
        self.assertFalse(self.filter.is_invalid_field('author.name', view))

        # No defined relationships
        class _BookView(BookView):
            ordering_fields = '__all__'
            relationships = None

        view = _BookView()
        self.assertTrue(self.filter.is_invalid_field('author.name', view))

        # Attempted related lookup on plain attribute
        class _BookView(BookView):
            ordering_fields = '__all__'
        self.assertTrue(self.filter.is_invalid_field('title.foo', view))


class RelatedOrderingFilterInterfaceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        book = models.Book.objects.create(
            author=models.Author.objects.create(name="Bob Robertson"),
            cover=models.Cover.objects.create(text="Bleep blep"),
            title="Ancient Aliens",
        )
        book.tags.add(models.Tag.objects.create(text="Historical Fiction"))

        book = models.Book.objects.create(
            author=models.Author.objects.create(name="Charles Charleston"),
            cover=models.Cover.objects.create(text="Grwarr"),
            title="Future Dinosaurs",
        )
        book.tags.add(models.Tag.objects.create(text="Science Fiction"))

    def test_attribute_ordering(self):
        view = BookView.as_view()
        request = factory.get('/', {'sort': 'title'})
        response = view(request)

        data = response.data['data']
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['attributes']['title'], "Ancient Aliens")
        self.assertEqual(data[1]['attributes']['title'], "Future Dinosaurs")

        # reverse case
        request = factory.get('/', {'sort': '-title'})
        response = view(request)

        data = response.data['data']
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['attributes']['title'], "Future Dinosaurs")
        self.assertEqual(data[1]['attributes']['title'], "Ancient Aliens")

    def test_forwards_FK_ordering(self):
        view = BookView.as_view()
        request = factory.get('/', {'sort': 'author'})
        response = view(request)

        data = response.data['data']

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['attributes']['title'], "Ancient Aliens")
        self.assertEqual(data[1]['attributes']['title'], "Future Dinosaurs")

        # reverse case
        request = factory.get('/', {'sort': '-author'})
        response = view(request)

        data = response.data['data']
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['attributes']['title'], "Future Dinosaurs")
        self.assertEqual(data[1]['attributes']['title'], "Ancient Aliens")

    def test_related_attribute_ordering(self):
        view = BookView.as_view()
        request = factory.get('/', {'sort': 'author.name'})
        response = view(request)

        data = response.data['data']

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['attributes']['title'], "Ancient Aliens")
        self.assertEqual(data[1]['attributes']['title'], "Future Dinosaurs")

        # reverse case
        request = factory.get('/', {'sort': '-author.name'})
        response = view(request)

        data = response.data['data']
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['attributes']['title'], "Future Dinosaurs")
        self.assertEqual(data[1]['attributes']['title'], "Ancient Aliens")

    def test_invalid_related_ordering(self):
        class _BookView(BookView):
            ordering_fields = []

        view = _BookView.as_view()
        request = factory.get('/', {'sort': 'author'})
        response = view(request)

        self.assertEqual(response.status_code, 400)
        self.assertNotIn('data', response.data)

        errors = response.data['errors']
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['source']['parameter'], 'sort')
        self.assertIn('author', errors[0]['detail'], )

    def test_invalid_related_attribute_ordering(self):
        class _AuthorView(AuthorView):
            ordering_fields = None

        class _BookView(BookView):
            ordering_fields = ['author']
            relationships = [rel('author', _AuthorView), ]

        view = _BookView.as_view()
        request = factory.get('/', {'sort': 'author.name'})
        response = view(request)

        self.assertEqual(response.status_code, 400)
        self.assertNotIn('data', response.data)

        errors = response.data['errors']
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['source']['parameter'], 'sort')
        self.assertIn('author.name', errors[0]['detail'])


class FieldLookupFilterInterfaceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        book = models.Book.objects.create(
            author=models.Author.objects.create(name="Bob Robertson"),
            cover=models.Cover.objects.create(text="Bleep blep"),
            title="Ancient Aliens",
        )
        book.tags.add(models.Tag.objects.create(text="Historical Fiction"))

        book = models.Book.objects.create(
            author=models.Author.objects.create(name="Charles Charleston"),
            cover=models.Cover.objects.create(text="Grwarr"),
            title="Future Dinosaurs",
        )
        book.tags.add(models.Tag.objects.create(text="Science Fiction"))

    def test_lookup_parsing(self):
        class _BookView(BookView):
            filter_fields = ['author']

        view = _BookView.as_view()
        request = factory.get('/', {'filter[author]': 1})
        response = view(request)

        data = response.data['data']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['attributes']['title'], "Ancient Aliens")

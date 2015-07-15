
from unittest import TestCase as UTestCase
from django.test import TestCase
from rest_framework import serializers

from json_api.utils import import_class
from json_api.utils.model_meta import get_field_info, verbose_name
from json_api.utils.view_meta import get_field_attnames
from json_api.utils.rels import rel, model_rel

from tests.models import Parent, Child, Proxy, Related
from tests.views import BookView


class Import:
    pass


class TestImportClass(UTestCase):

    def test_dotted_notation(self):
        cls = import_class('tests.test_utils.Import')
        self.assertIs(cls, Import)

    def test_colon_notation(self):
        cls = import_class('tests.test_utils:Import')
        self.assertIs(cls, Import)


class TestVerboseName(TestCase):

    @classmethod
    def setUpTestData(cls):
        Parent.objects.create(parent_field='foo')
        Child.objects.create(parent_field='bar', child_field='baz')

    def test_verbose_name(self):
        self.assertEqual('parent', verbose_name(Parent))

    def test_proxy(self):
        # TODO: Is this the correct behavior?
        self.assertEqual('proxy', verbose_name(Proxy))

    def test_deferred_query(self):
        # `defer`red and `only` queries mangle the `verbose_name` attribute with
        # a list of the query's deferred fields.
        self.assertEqual('parent', verbose_name(Parent.objects.only('pk').first()))
        self.assertEqual('parent', verbose_name(Parent.objects.defer('parent_field').first()))


class TestModelMeta(TestCase):

    def test_drf_consistency(self):
        # make sure that DRF's model_meta implementation is still working roughly as expected
        from rest_framework.utils.model_meta import get_field_info
        info = get_field_info(Related)

        self.assertEqual(info.reverse_relations.keys(), ['otherrelated_set'])
        self.assertEqual(info.relations.keys(), ['parent', 'otherrelated_set'])

    def test_name_translation(self):
        info = get_field_info(Related)

        self.assertEqual(info.reverse_relations.keys(), ['otherrelated'])
        self.assertEqual(info.relations.keys(), ['parent', 'otherrelated'])


class TestRels(UTestCase):

    def test_rel(self):
        self.assertEqual(
            rel('a', 'b')._asdict(),
            {'relname': 'a', 'viewset': 'b', 'attname': 'a'}
        )

        self.assertEqual(
            rel('a', 'b', 'c')._asdict(),
            {'relname': 'a', 'viewset': 'b', 'attname': 'c'}
        )

    def test_model_rel(self):
        m = model_rel('a', 'a', 'tests.test_utils.Import', None, None)
        self.assertEqual(m.viewset.__class__, Import)

        m = model_rel('a', 'a', Import(), None, None)
        self.assertEqual(m.viewset.__class__, Import)

        m = model_rel('a', 'a', Import, None, None)
        self.assertEqual(m.viewset.__class__, Import)

        self.assertIsNone(m.viewset.request)


class TestViewMeta(TestCase):

    def test_field_attnames(self):
        actual = get_field_attnames(BookView)
        expected = {
            'title': 'title',
            'author': 'author',
            'cover': 'cover',
            'tags': 'tags',
        }
        self.assertEqual(actual, expected)

    def test_field_attnames_alternate_names(self):
        BookSerializer = BookView.serializer_class

        class AltBookSerializer(BookSerializer):
            alt_title = serializers.CharField(source='title')

            class Meta(BookSerializer.Meta):
                fields = ['alt_title', ]

        class AltBookView(BookView):
            serializer_class = AltBookSerializer

            relationships = [
                rel('author', 'tests.test_filters.AuthorView', 'foo'),
            ]

        actual = get_field_attnames(AltBookView)
        expected = {
            'alt_title': 'title',
            'author': 'foo',
        }
        self.assertEqual(actual, expected)

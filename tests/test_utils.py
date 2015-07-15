
from unittest import TestCase as UTestCase
from django.test import TestCase

from json_api.utils import import_class
from json_api.utils.model_meta import get_field_info, verbose_name
from json_api.utils.rels import rel, model_rel

from tests.models import Parent, Child, Proxy, Related


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

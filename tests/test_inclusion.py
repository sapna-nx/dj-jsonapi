
from unittest import TestCase as UTestCase
from django.test import TestCase, override_settings
from django.conf.urls import url
from rest_framework.test import APIRequestFactory
# from rest_framework import serializers
from json_api import inclusion
from json_api.utils.rels import rel

from tests import views, models

factory = APIRequestFactory()


# forward/reverse relationship testing generic views
class PersonView(views.ListMixin, views.PersonView):
    inclusion_class = inclusion.RelatedResourceInclusion
    include_rels = '__all__'

    relationships = [
        rel('articles', 'tests.test_inclusion.ArticleView', 'article'),
    ]


class ArticleView(views.ListMixin, views.ArticleView):
    inclusion_class = inclusion.RelatedResourceInclusion
    include_rels = '__all__'

    relationships = [
        rel('author', 'tests.test_inclusion.PersonView'),
        rel('comments', 'tests.test_inclusion.CommentView', 'comment'),
    ]


class CommentView(views.ListMixin, views.CommentView):
    inclusion_class = inclusion.RelatedResourceInclusion
    include_rels = '__all__'

    relationships = [
        rel('author', 'tests.test_inclusion.PersonView'),
        rel('article', 'tests.test_inclusion.ArticleView'),
    ]


class ArticleDetailView(views.DetailMixin, views.ArticleView):
    inclusion_class = inclusion.RelatedResourceInclusion
    include_rels = '__all__'

    relationships = [
        rel('author', 'tests.test_inclusion.PersonView'),
        rel('comments', 'tests.test_inclusion.CommentView', 'comment'),
    ]

urlpatterns = [
    url(r'^(?P<pk>\d+)/$', ArticleDetailView.as_view(), name='detail-view'),
]


class RelatedResourceInclusionTests(UTestCase):

    def setUp(self):
        self.includer = inclusion.RelatedResourceInclusion()

    def test_group_include_paths(self):
        i = self.includer

        self.assertEqual(
            i.group_include_paths(['a', 'b', 'c']),
            {'a': [], 'b': [], 'c': []}
        )

        self.assertEqual(
            i.group_include_paths(['a', 'a.b', 'a.c', 'b']),
            {'a': ['b', 'c'], 'b': []}
        )

        self.assertEqual(
            i.group_include_paths(['a', 'a.b', 'a.c.d', 'b']),
            {'a': ['b', 'c.d'], 'b': []}
        )

    def test_get_includable_rels(self):
        class NoDefinedFields(ArticleView):
            include_rels = None

        class AllFields(ArticleView):
            include_rels = '__all__'

        class FieldSubset(ArticleView):
            include_rels = ['author']

        class InvalidFields(ArticleView):
            include_rels = ['foo', 'bar']

        view = NoDefinedFields()
        self.assertEqual(self.includer.get_includable_rels(view), [])

        view = AllFields()
        self.assertEqual(self.includer.get_includable_rels(view), ['author', 'comments'])

        view = FieldSubset()
        self.assertEqual(self.includer.get_includable_rels(view), ['author'])

        view = InvalidFields()
        with self.assertRaisesRegexp(AssertionError, 'must be valid resource relnames'):
            self.includer.get_includable_rels(view)

    def test_is_invalid_include(self):
        class NoDefinedIncludes(ArticleView):
            include_rels = None

        class AllIncludes(ArticleView):
            include_rels = '__all__'

        class IncludeSubset(ArticleView):
            include_rels = ['author']

        view = NoDefinedIncludes()
        self.assertTrue(self.includer.is_invalid_include('author', view))
        self.assertTrue(self.includer.is_invalid_include('comments', view))

        view = AllIncludes()
        self.assertFalse(self.includer.is_invalid_include('author', view))
        self.assertFalse(self.includer.is_invalid_include('comments', view))

        view = IncludeSubset()
        self.assertFalse(self.includer.is_invalid_include('author', view))
        self.assertTrue(self.includer.is_invalid_include('comments', view))

    def test_is_invalid_include_for_related(self):
        class NoDefinedIncludes(ArticleView):
            include_rels = None

        class AllIncludes(ArticleView):
            include_rels = '__all__'

        # Invalid author attribute lookup
        class _CommentView(CommentView):
            include_rels = '__all__'
            relationships = [rel('article', NoDefinedIncludes), ]

        view = _CommentView()
        self.assertFalse(self.includer.is_invalid_include('article', view))
        self.assertTrue(self.includer.is_invalid_include('article.author', view))

        # Valid author attribute lookup
        class _CommentView(CommentView):
            include_rels = '__all__'
            relationships = [rel('article', AllIncludes), ]

        view = _CommentView()
        self.assertFalse(self.includer.is_invalid_include('article', view))
        self.assertFalse(self.includer.is_invalid_include('article.author', view))

        # No defined relationships
        class _CommentView(CommentView):
            include_rels = '__all__'
            relationships = None

        view = _CommentView()
        self.assertTrue(self.includer.is_invalid_include('article', view))
        self.assertTrue(self.includer.is_invalid_include('article.author', view))

        # Attempted related lookup on plain attribute
        class _CommentView(CommentView):
            include_rels = '__all__'
        self.assertTrue(self.includer.is_invalid_include('article.title', view))


@override_settings(ROOT_URLCONF='tests.test_inclusion')
class RelatedResourceInclusionInterfaceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        dgeb = models.Person.objects.create(name='Dan Gebhardt')
        katz = models.Person.objects.create(name='Yehuda Katz')
        klab = models.Person.objects.create(name='Steve Klabnik')

        article = models.Article.objects.create(
            author=dgeb,
            title='JSON API paints my bikeshed!'
        )

        models.Comment.objects.create(author=katz, article=article, body='foo bar')
        models.Comment.objects.create(author=klab, article=article, body='bar baz')
        models.Comment.objects.create(author=katz, article=article, body='baz qux')

        article = models.Article.objects.create(
            author=dgeb,
            title='Wicked Good Ember 2014'
        )

        models.Comment.objects.create(author=katz, article=article, body='a 1')
        models.Comment.objects.create(author=klab, article=article, body='b 2')
        models.Comment.objects.create(author=katz, article=article, body='c 3')

        article = models.Article.objects.create(
            author=klab,
            title='Ouroboros'
        )

        models.Comment.objects.create(author=katz, article=article, body='abc')
        models.Comment.objects.create(author=dgeb, article=article, body='def')
        models.Comment.objects.create(author=katz, article=article, body='hij')

    def test_forward_to_one_include(self):
        view = ArticleView.as_view()
        request = factory.get('/', {'include': 'author'})
        response = view(request)

        data = response.data['data']
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]['attributes']['title'], "JSON API paints my bikeshed!")
        self.assertEqual(data[1]['attributes']['title'], "Wicked Good Ember 2014")
        self.assertEqual(data[2]['attributes']['title'], "Ouroboros")

        included = response.data['included']
        self.assertEqual(len(included), 2)
        self.assertEqual(included[0]['attributes']['name'], "Dan Gebhardt")
        self.assertEqual(included[1]['attributes']['name'], "Steve Klabnik")

        # nested relationship
        view = CommentView.as_view()
        request = factory.get('/', {'include': 'article.author'})
        response = view(request)

        data = response.data['data']
        self.assertEqual(len(data), 9)

        # 2 authors, 3 articles
        included = response.data['included']
        self.assertEqual(len(included), 5)

        authors = [inst for inst in included if inst['type'] == 'person']
        self.assertEqual(len(authors), 2)

        articles = [inst for inst in included if inst['type'] == 'article']
        self.assertEqual(len(articles), 3)

    def test_reverse_to_many_include(self):
        view = PersonView.as_view()
        request = factory.get('/', {'include': 'articles'})
        response = view(request)

        data = response.data['data']
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]['attributes']['name'], "Dan Gebhardt")
        self.assertEqual(data[1]['attributes']['name'], "Yehuda Katz")
        self.assertEqual(data[2]['attributes']['name'], "Steve Klabnik")

        included = response.data['included']
        self.assertEqual(len(included), 3)
        self.assertEqual(included[0]['attributes']['title'], "JSON API paints my bikeshed!")
        self.assertEqual(included[1]['attributes']['title'], "Wicked Good Ember 2014")
        self.assertEqual(included[2]['attributes']['title'], "Ouroboros")

        # nested relationship
        request = factory.get('/', {'include': 'articles.comments'})
        response = view(request)

        data = response.data['data']
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]['attributes']['name'], "Dan Gebhardt")
        self.assertEqual(data[1]['attributes']['name'], "Yehuda Katz")
        self.assertEqual(data[2]['attributes']['name'], "Steve Klabnik")

        # 3 articles, 9 comments
        included = response.data['included']
        self.assertEqual(len(included), 12)

        authors = [inst for inst in included if inst['type'] == 'article']
        self.assertEqual(len(authors), 3)

        articles = [inst for inst in included if inst['type'] == 'comment']
        self.assertEqual(len(articles), 9)

    def test_include_on_instance(self):
        response = self.client.get('/1/', {'include': 'author'})

        data = response.data['data']
        self.assertEqual(data['attributes']['title'], "JSON API paints my bikeshed!")

        included = response.data['included']
        self.assertEqual(len(included), 1)
        self.assertEqual(included[0]['attributes']['name'], "Dan Gebhardt")

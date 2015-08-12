
import json
from django.test import TestCase
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory

from django_fantasy import models

factory = APIRequestFactory()


class TestToOneRelationship(TestCase):
    fixtures = ['fantasy-database']

    def test_get_relationship(self):
        response = self.client.get(
            reverse('book-relationship', kwargs={'pk': 1, 'relname': 'author'})
        )

        data = response.data['data']

        self.assertEqual(data['type'], 'author')
        self.assertEqual(data['id'], 1)

    def test_set_relationship(self):
        """
        PATCH an empty relationship with data to set a relationship.
        """
        # The hobbit does not belong to a series
        hobbit = models.Book.objects.get(pk=11)
        self.assertEqual(hobbit.title, 'The Hobbit')
        self.assertIsNone(hobbit.series)

        response = self.client.patch(
            reverse('book-relationship', kwargs={'pk': 11, 'relname': 'series'}),
            data=json.dumps({"data": {"type": "series", "id": 1}}),
            content_type='application/json')

        # expect HTTP 204
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # assert that The Hobbit now belongs LotR
        hobbit = models.Book.objects.get(pk=11)
        self.assertEqual(hobbit.title, 'The Hobbit')
        self.assertEqual(hobbit.series.pk, 1)
        self.assertEqual(hobbit.series.title, 'The Lord of the Rings')

    def test_unset_relationship(self):
        """
        PATCH a relationship with null data to unset a relationship.
        """
        # The Fellowship of the Ring belongs to LotR
        fellowship = models.Book.objects.get(pk=1)
        self.assertEqual(fellowship.title, 'The Fellowship of the Ring')
        self.assertEqual(fellowship.series.pk, 1)

        response = self.client.patch(
            reverse('book-relationship', kwargs={'pk': 1, 'relname': 'series'}),
            data=json.dumps({"data": None}),
            content_type='application/json')

        # expect HTTP 204
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # assert that The Fellowship of the Ring now belongs to no man
        fellowship = models.Book.objects.get(pk=1)
        self.assertEqual(fellowship.title, 'The Fellowship of the Ring')
        self.assertIsNone(fellowship.series)

    def test_replace_relationship(self):
        """
        PATCH a relationship with new document data to replace a relationship.
        """
        # The Fellowship of the Ring belongs to LotR
        fellowship = models.Book.objects.get(pk=1)
        self.assertEqual(fellowship.title, 'The Fellowship of the Ring')
        self.assertEqual(fellowship.series.pk, 1)

        response = self.client.patch(
            reverse('book-relationship', kwargs={'pk': 1, 'relname': 'series'}),
            data=json.dumps({"data": {"type": "series", "id": 2}}),
            content_type='application/json')

        # expect HTTP 204
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # assert that The Fellowship of the Ring is misfiled
        fellowship = models.Book.objects.get(pk=1)
        self.assertEqual(fellowship.title, 'The Fellowship of the Ring')
        self.assertEqual(fellowship.series.pk, 2)
        self.assertEqual(fellowship.series.title, 'Harry Potter')

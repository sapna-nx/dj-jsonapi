
import json
from unittest import skip
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory

from django_fantasy import models

factory = APIRequestFactory()


class ToOneRelationships(TestCase):
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
            content_type='application/vnd.api+json',
        )

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
            content_type='application/vnd.api+json',
        )

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
            content_type='application/vnd.api+json',
        )

        # expect HTTP 204
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # assert that The Fellowship of the Ring is misfiled
        fellowship = models.Book.objects.get(pk=1)
        self.assertEqual(fellowship.title, 'The Fellowship of the Ring')
        self.assertEqual(fellowship.series.pk, 2)
        self.assertEqual(fellowship.series.title, 'Harry Potter')

    def test_forwards_unset_non_nullable(self):
        # The fellowship was written by Tolkien
        fellowship = models.Book.objects.get(pk=1)
        self.assertEqual(fellowship.title, 'The Fellowship of the Ring')

        # author should be Tolkien
        self.assertEqual(fellowship.author.pk, 1)
        self.assertEqual(fellowship.author.name, 'J. R. R. Tolkien')

        # attempt to unset the author
        response = self.client.patch(
            reverse('book-relationship', kwargs={'pk': 1, 'relname': 'author'}),
            data=json.dumps({"data": None}),
            content_type='application/vnd.api+json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(len(response.data['errors']), 1)

        # Tolkien should still be the author
        fellowship = models.Book.objects.get(pk=1)
        self.assertEqual(fellowship.author.pk, 1)
        self.assertEqual(fellowship.author.name, 'J. R. R. Tolkien')

    @skip('Need to implement generic relationships')
    def test_reverse_unset_non_nullable(self):
        pass

    def test_method_unallowed(self):
        """
        POST and DELETE should not be allowed for to-one relationships
        """
        # POST
        response = self.client.post(
            reverse('book-relationship', kwargs={'pk': 1, 'relname': 'author'}),
            content_type='application/vnd.api+json',
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # DELETE
        response = self.client.delete(
            reverse('book-relationship', kwargs={'pk': 1, 'relname': 'author'}),
            content_type='application/vnd.api+json',
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ToManyRelationships(TestCase):
    fixtures = ['fantasy-database']

    def test_get_relationship(self):
        response = self.client.get(
            reverse('book-relationship', kwargs={'pk': 1, 'relname': 'author'})
        )

        data = response.data['data']

        self.assertEqual(data['type'], 'author')
        self.assertEqual(data['id'], 1)

    def test_null_data(self):
        """
        null data should not be allowed for a to-many request
        """
        c = self.client

        for method in (c.post, c.patch, c.delete):
            response = method(
                reverse('book-relationship', kwargs={'pk': 1, 'relname': 'chapters'}),
                data=json.dumps({"data": None}),
                content_type='application/vnd.api+json',
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(len(response.data['errors']), 1)
            self.assertEqual(
                response.data['errors'][0]['detail'],
                'This field may not be null.'
            )

    def test_empty_data(self):
        """
        Empty data should have no effect unless PATCHing the relationship.
        """
        # The Lord of the Rings has 3 books
        lotr = models.Series.objects.get(pk=1)
        self.assertEqual(lotr.book_set.count(), 3)

        # should be a noop
        for method in (self.client.post, self.client.delete):
            response = method(
                reverse('series-relationship', kwargs={'pk': 1, 'relname': 'books'}),
                data=json.dumps({"data": []}),
                content_type='application/vnd.api+json',
            )
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

            # assert that the books are unchanged
            lotr = models.Series.objects.get(pk=1)
            self.assertEqual(lotr.book_set.count(), 3)

        # replace the collection with an empty array
        response = self.client.patch(
            reverse('series-relationship', kwargs={'pk': 1, 'relname': 'books'}),
            data=json.dumps({"data": []}),
            content_type='application/vnd.api+json',
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # assert that there are no books
        lotr = models.Series.objects.get(pk=1)
        self.assertEqual(lotr.book_set.count(), 0)

    def test_reverse_unset_non_nullable(self):
        # Tolkien wrote LotR and The Hobbit
        tolkien = models.Author.objects.get(pk=1)
        self.assertEqual(tolkien.name, 'J. R. R. Tolkien')

        # Published works should contain 4 books, including The Hobbit
        self.assertEqual(tolkien.book_set.count(), 4)
        self.assertEqual(tolkien.book_set.get(pk=11).title, 'The Hobbit')

        # attempt to remove The Hobbit
        response = self.client.delete(
            reverse('author-relationship', kwargs={'pk': 1, 'relname': 'books'}),
            data=json.dumps({"data": [{'type': 'book', 'id': 11}]}),
            content_type='application/vnd.api+json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(len(response.data['errors']), 1)

        # attempt to only include The Hobbit
        response = self.client.patch(
            reverse('author-relationship', kwargs={'pk': 1, 'relname': 'books'}),
            data=json.dumps({"data": [{'type': 'book', 'id': 11}]}),
            content_type='application/vnd.api+json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(len(response.data['errors']), 1)

        # Published works should still contain 4 books
        tolkien = models.Author.objects.get(pk=1)
        self.assertEqual(tolkien.book_set.count(), 4)
        self.assertEqual(tolkien.book_set.get(pk=11).title, 'The Hobbit')

    def test_add_to_relationship(self):
        """
        POST data to add to a relationship.
        """
        # The Hobbit does not belong to a series
        hobbit = models.Book.objects.get(pk=11)
        self.assertEqual(hobbit.title, 'The Hobbit')
        self.assertIsNone(hobbit.series)

        # Add The Hobbit to the LotR series
        response = self.client.patch(
            reverse('book-relationship', kwargs={'pk': 11, 'relname': 'series'}),
            data=json.dumps({"data": {"type": "series", "id": 1}}),
            content_type='application/vnd.api+json',
        )

        # expect HTTP 204
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # assert that The Hobbit now belongs LotR
        hobbit = models.Book.objects.get(pk=11)
        self.assertEqual(hobbit.title, 'The Hobbit')
        self.assertEqual(hobbit.series.pk, 1)
        self.assertEqual(hobbit.series.title, 'The Lord of the Rings')

    def test_set_relationship(self):
        """
        PATCH data to set a relationship.
        """
        # The LotR has three books.
        lotr = models.Series.objects.get(pk=1)
        self.assertEqual(lotr.title, 'The Lord of the Rings')
        self.assertEqual(lotr.book_set.count(), 3)
        self.assertSequenceEqual(lotr.book_set.values_list('id', flat=True), [1, 2, 3])

        # But hear me out, what if... we turned The Hobbit into a trilogy
        response = self.client.patch(
            reverse('series-relationship', kwargs={'pk': 1, 'relname': 'books'}),
            data=json.dumps({"data": [{'type': 'book', 'id': 11}]}),
            content_type='application/vnd.api+json',
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # The LotR should now contain only The Hobbit
        lotr = models.Series.objects.get(pk=1)
        self.assertEqual(lotr.book_set.count(), 1)
        self.assertSequenceEqual(lotr.book_set.values_list('id', flat=True), [11])

    def test_reset_relationship(self):
        """
        PATCHing a relationship with its same data should have no effect.
        For non-nullable relationships, a 403 should NOT be raised.
        """
        # Tolkien has written 4 books
        tolkien = models.Author.objects.get(pk=1)
        self.assertEqual(tolkien.book_set.count(), 4)
        self.assertSequenceEqual(tolkien.book_set.values_list('id', flat=True), [1, 2, 3, 11])

        # Set the written works to his current written works
        response = self.client.patch(
            reverse('author-relationship', kwargs={'pk': 1, 'relname': 'books'}),
            data=json.dumps({"data": [
                {'type': 'book', 'id': 1}, {'type': 'book', 'id': 2},
                {'type': 'book', 'id': 3}, {'type': 'book', 'id': 11},
            ]}),
            content_type='application/vnd.api+json',
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Tolkien should still have 4 books
        tolkien = models.Author.objects.get(pk=1)
        self.assertEqual(tolkien.book_set.count(), 4)
        self.assertSequenceEqual(tolkien.book_set.values_list('id', flat=True), [1, 2, 3, 11])

    def test_remove_from_relationship(self):
        """
        DELETE data to remove from a relationship.
        """
        # The LotR has three books.
        lotr = models.Series.objects.get(pk=1)
        self.assertEqual(lotr.title, 'The Lord of the Rings')
        self.assertEqual(lotr.book_set.count(), 3)
        self.assertSequenceEqual(lotr.book_set.values_list('id', flat=True), [1, 2, 3])

        # Remove the books from the series
        response = self.client.delete(
            reverse('series-relationship', kwargs={'pk': 1, 'relname': 'books'}),
            data=json.dumps({"data": [
                {'type': 'book', 'id': 1},
                {'type': 'book', 'id': 2},
                {'type': 'book', 'id': 3},
            ]}),
            content_type='application/vnd.api+json',
        )

        # expect HTTP 204
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # assert that LotR has no books
        lotr = models.Series.objects.get(pk=1)
        self.assertEqual(lotr.title, 'The Lord of the Rings')
        self.assertEqual(lotr.book_set.count(), 0)

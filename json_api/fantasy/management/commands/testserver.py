
import os
import json
import requests
from django.contrib.contenttypes.models import ContentType
from django.core.management.commands import testserver


class Command(testserver.Command):

    def translate_fixture(self, data):
        results = []

        # first, check out expected keys
        assert set(data.keys()) == {'authors', 'series', 'books', 'chapters', 'stores', 'books_stores', 'photos'}

        for author in data['authors']:
            results.append({
                'pk': author['id'], 'model': 'fantasy.author',
                'fields': {
                    'name': author['name'],
                    'date_of_birth': author['date_of_birth'],
                    'date_of_death': author['date_of_death'],
                }
            })

        for series in data['series']:
            results.append({
                'pk': series['id'], 'model': 'fantasy.series',
                'fields': {
                    'title': series['title'],
                }
            })

        for book in data['books']:
            results.append({
                'pk': book['id'], 'model': 'fantasy.book',
                'fields': {
                    'series': book['series_id'],
                    'author': book['author_id'],
                    'title': book['title'],
                    'date_published': book['date_published'],
                }
            })

        for chapter in data['chapters']:
            results.append({
                'pk': chapter['id'], 'model': 'fantasy.chapter',
                'fields': {
                    'title': chapter['title'],
                    'book': chapter['book_id'],
                    'ordering': chapter['ordering'],
                }
            })

        for store in data['stores']:
            results.append({
                'pk': store['id'], 'model': 'fantasy.store',
                'fields': {
                    'name': store['name'],
                    'books': [sb['book_id'] for sb in data['books_stores'] if sb['store_id'] == store['id']],
                }
            })

        for photo in data['photos']:
            types_map = {
                'authors': ContentType.objects.get(app_label='fantasy', model='author').pk,
                'books': ContentType.objects.get(app_label='fantasy', model='book').pk,
                'series': ContentType.objects.get(app_label='fantasy', model='series').pk,
            }

            results.append({
                'pk': photo['id'], 'model': 'fantasy.photo',
                'fields': {
                    'imageable_id': photo['imageable_id'],
                    'imageable_type': types_map[photo['imageable_type']],
                    'title': photo['title'],
                    'uri': photo['uri'],
                }
            })

        return results

    def handle(self, *fixture_labels, **options):
        label = 'fantasy.json'

        response = requests.get('https://raw.githubusercontent.com/endpoints/fantasy-database/master/data.json')
        data = response.json()

        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')

        with open(path, 'w') as f:
            try:
                data = self.translate_fixture(data)
                f.write(json.dumps(data))

                label = path
            except AssertionError:
                pass

        fixture_labels += (label, )

        super(Command, self).handle(*fixture_labels, **options)

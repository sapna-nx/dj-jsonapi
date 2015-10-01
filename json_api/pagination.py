
'''
This module provides simple wrappers around the pagination classes provided in
the `rest_framework.pagination` module. They attempt to bring DRF pagination
into conformance with json-api pagination by addining the following:

- `get_first_link()`
- `get_last_link()`
- `get_links()`

Reference:
http://jsonapi.org/format/#fetching-pagination

'''

from collections import OrderedDict
from rest_framework import pagination
from rest_framework.utils.urls import (
    replace_query_param, remove_query_param
)


class PageLinksMixin(object):

    def get_first_link(self):
        pass

    def get_last_link(self):
        pass

    def get_links(self):
        first_link = self.get_first_link()
        last_link = self.get_last_link()
        prev_link = self.get_previous_link()
        next_link = self.get_next_link()

        links = OrderedDict()
        if first_link:
            links['first'] = first_link
        if last_link:
            links['last'] = last_link
        if prev_link:
            links['prev'] = prev_link
        if next_link:
            links['next'] = next_link

        return links


class PageNumberPagination(pagination.PageNumberPagination, PageLinksMixin):
    @property
    def paginator(self):
        return self.page.paginator

    def get_first_link(self):
        url = self.request.build_absolute_uri()
        return remove_query_param(url, self.page_query_param)

    def get_last_link(self):
        url = self.request.build_absolute_uri()
        page_number = self.paginator.num_pages

        # only add a 'last' link if it isn't going to be the same as the 'first' link.
        if page_number != 1:
            return replace_query_param(url, self.page_query_param, page_number)

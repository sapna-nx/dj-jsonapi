
def unquote_brackets(url):
    if '?' not in url:
        return url

    url, query = url.split('?', 1)
    query = query.replace('%5B', '[')
    query = query.replace('%5D', ']')
    return '?'.join([url, query])

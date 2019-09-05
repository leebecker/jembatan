import urllib.request
from jembatan.core.spandex import Spandex, constants

def uri_to_spndx(uri, viewname=None):
    if not viewname:
        viewname = constants.SPANDEX_DEFAULT_VIEW
    url = urllib.request.urlparse(uri)
    fh = open(uri) if not url.scheme else urllib.request.urlopen(uri)

    spndx = Spandex()
    view = spndx.get_or_create_view(viewname)
    view.content_string = fh.read()
    view.content_mime = "text/plain"
    return spndx


class UriSpandexCollection:

    def __init__(self, uris):
        """
        @param uris - iterable of uri or local path strings
        """
        self.uris = uris

    def __iter__(self):
        for uri in self.uris:
            spndx = Spandex()
            view = spndx.create_view(constants.SPANDEX_URI_VIEW, content_string=uri, content_mime="text/uri")
            yield spndx


class UriToPlainTextAnalyzer:

    def __init__(self, tgt_viewname=None):
        self.tgt_viewname = tgt_viewname if tgt_viewname else constants.SPANDEX_DEFAULT_VIEW
        pass

    def process(self, spndx):
        uri_view = spndx.get_view(constants.SPANDEX_URI_VIEW)

        uri = uri_view.content_string
        url = urllib.request.urlparse(uri)
        fh = open(uri) if not url.scheme else urllib.request.urlopen(uri)
        tgt_view = spndx.get_or_create_view(self.tgt_viewname)
        tgt_view.content_string = fh.read()
        tgt_view.content_mime = "text/plain"

from jembatan.core.spandex import Spandex


def text_to_spandex(text):
    """
    Create unadorned plaintext cas
    """
    spndx = Spandex(content_string=text, content_mime="text/plain")
    return spndx


class TextSpandexCollection():
    """
    Given collection of texts transform into collection of Spandexes
    """

    def __init__(self, texts):
        """
        @param uris - iterable of uri or local path strings
        """
        self.texts

    def __iter__(self):
        for text in self.texts:
            yield text_to_spandex(text)




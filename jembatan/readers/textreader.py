from jembatan.core.spandex import JembatanDoc


def text_to_jembatan_doc(text):
    """
    Create Jembatan with text populating default view
    """
    jem = JembatanDoc(content_string=text, content_mime="text/plain")
    return jem


class TextJemdocCollection():
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
            yield text_to_jembatan_doc(text)

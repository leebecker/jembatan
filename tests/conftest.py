import pytest

@pytest.yield_fixture(scope="function")
def sample_texts(request):
    return [
        """
        This is sentence 1.  Sentence two follows.   Sentence three
        comes last.


        Making a new paragraph.  This one should also have three sentences.
        Now it does.
        """
    ]

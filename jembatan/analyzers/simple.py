from jembatan.core.af import AnalysisFunction
from jembatan.core.spandex import Span, Spandex
from jembatan.typesys import Annotation
from typing import Pattern

import re


class RegexMatchAnnotator(AnalysisFunction):
    """
    Spandex AnalysisFunction which will find matches from the specified regular expression and will create
    the corresponding annotation type when found over the view
    """
    def __init__(self, match_re: Pattern[str], annotation_type: Annotation, window_type: Annotation=None):
        """
        Creates Spandex RegexMatch Analyzer

        @param match_re - regular expression specifying match parameters
        @param annotation_type - annotation type to create for matching spans
        @param window_type - annotation type over which to run analyses (i.e. over sentences, paragraphs, etc)
        """
        self.match_re = match_re
        self.annotation_type = annotation_type
        self.window_type = window_type

    def process(self, spndx: Spandex):
        if self.window_type:
            windows = [window.span for window in spndx.select(self.window_type)]
        else:
            windows = [Span(0, len(spndx.content_string))]

        annotations = []
        for window in windows:
            window_text = spndx.spanned_text(window)

            for match in self.match_re.finditer(window_text):
                mbeg, mend = match.span()
                annotation = self.annotation_type()
                annotation.span = Span(begin=window.begin+mbeg, end=window.begin+mend)
                annotations.append(annotation)
        spndx.add_annotations(*annotations)


class RegexSplitAnnotator(AnalysisFunction):
    """
    Spandex AnalysisFunction which will split view content based on the splitting regex.  Not splitting
    matches become annotations.
    """

    def __init__(self, split_re: Pattern[str], annotation_type: Annotation, window_type: Annotation=None):
        """
        Creates Spandex Regex Split Analyzer

        @param split_re - regular expression to split view content on
        @param annotation_type - annotation type to create for matching spans
        @param window_type - annotation type over which to run analyses (i.e. over sentences, paragraphs, etc)
        """
        self.split_re = split_re
        self.annotation_type = annotation_type
        self.window_type = window_type

    def process(self, spndx: Spandex):
        if self.window_type:
            windows = [window.span for window in spndx.select(self.window_type)]
        else:
            windows = [Span(0, len(spndx.content_string))]

        annotations = []
        for window in windows:
            window_text = spndx.spanned_text(window)

            matches = list(self.split_re.finditer(window_text))

            if not matches:
                # no split found so make the whole window paragraph
                span = Span(begin=window.begin+0, end=window.begin+len(spndx.content_string))
                annotation = self.annotation_type(begin=span.begin, end=span.end)
                annotations.append(annotation)
            else:
                if matches[0].span()[0] > 0:
                    span = Span(begin=window.begin+0, end=window.begin+matches[0].span()[0])
                    annotation = self.annotation_type(begin=span.begin, end=span.end)
                    annotations.append(annotation)

                for m0, m1 in zip(matches[0:-1], matches[1:]):
                    span = Span(begin=window.begin+m0.span()[1], end=window.begin+m1.span()[0])
                    annotation = self.annotation_type(begin=span.begin, end=span.end)
                    annotations.append(annotation)

                if matches[-1].span()[1] <= len(window_text):
                    # get straggling span
                    span = Span(begin=window.begin+matches[-1].span()[1], end=window.begin+len(spndx.content_string))
                    annotation = self.annotation_type(begin=span.begin, end=span.end)
                    annotations.append(annotation)

        spndx.add_annotations(*annotations)


class SimpleTokenizer:
    def __init__(self, window_type=None):
        from jembatan.typesys.segmentation import Token
        self.regex_annotator = RegexMatchAnnotator(re.compile("\w+"), Token, window_type=window_type)

    def process(self, spndx):
        self.regex_annotator.process(spndx)


class SimpleSentenceSegmenter:
    def __init__(self, window_type=None):
        from jembatan.typesys.segmentation import Sentence
        self.regex_annotator = RegexMatchAnnotator(
            re.compile(re.compile(r'[^\s\.][^\.]+')), Sentence, window_type=window_type)

    def process(self, spndx):
        self.regex_annotator.process(spndx)

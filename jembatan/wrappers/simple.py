from jembatan.core.af import AnalysisFunction
from jembatan.core.spandex import Span, Spandex
from jembatan.typesys import Annotation
from typing import Pattern


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
            windows = [window_span for window_span, _ in spndx.select(self.window_type)]
        else:
            windows = [Span(0, len(spndx.content_string))]

        annotations = []
        for window in windows:
            window_text = spndx.spanned(window)

            for match in self.match_re.finditer(window_text):
                mbeg, mend = match.span()
                span = Span(begin=window.begin+mbeg, end=window.begin+mend)
                annotation = self.annotation_type()
                annotations.append((span, annotation))
        spndx.add_layer(self.annotation_type, annotations)


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
            windows = [window_span for window_span, _ in spndx.select(self.window_type)]
        else:
            windows = [Span(0, len(spndx.content_string))]

        annotations = []
        for window in windows:
            window_text = spndx.spanned(window)

            matches = list(self.split_re.finditer(window_text))

            if not matches:
                # no split found so make the whole window paragraph
                span = Span(begin=window.begin+0, end=window.begin+len(spndx.content))
                annotation = self.annotation_type()
                annotations.append((span, annotation))
            else:
                if matches[0].span()[0] > 0:
                    span = Span(begin=window.begin+0, end=window.begin+matches[0].span()[0])
                    annotation = self.annotation_type()
                    annotations.append((span, annotation))

                for m0, m1 in zip(matches[0:-1], matches[1:]):
                    span = Span(begin=window.begin+m0.span()[1], end=window.begin+m1.span()[0])
                    annotation = self.annotation_type()
                    annotations.append((span, annotation))

                if matches[-1].span()[1] <= len(window_text):
                    # get straggling span
                    span = Span(begin=window.begin+matches[-1].span()[1], end=window.begin+len(spndx.content_string))
                    annotation = self.annotation_type()
                    annotations.append((span, annotation))

        spndx.add_layer(self.annotation_type, annotations)

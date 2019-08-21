from copy import deepcopy
from jembatan.core.af import AnalysisFunction
from jembatan.core.spandex import Span, Spandex
from jembatan.typesys import Annotation
from typing import Iterable


class BioChunking:
    """
    Helper class for converting between subchunks and chunks for BIO chunking tasks.
    """

    def _empty_suffix(self, chunk):
        return ""

    def _no_attribute(self, chunk, outcome):
        return

    def __init__(self, subchunk_type: Annotation, chunk_type: Annotation, suffix_func=None, attrib_func=None):

        self.subchunk_type = subchunk_type
        self.chunk_type = chunk_type
        self.suffix_func = self._empty_suffix if suffix_func is None else suffix_func
        self.attrib_func = self._no_attribute if attrib_func is None else attrib_func

    def parse_outcome(self, outcome):
        parts = outcome.split('-')
        prefix = parts[0]
        label = parts[1] if len(parts) > 1 else ""
        return prefix, label

    def create_outcomes(self, spndx: Spandex,
                        subchunks: Iterable[Annotation], chunks: Iterable[Annotation]):
        """
        """
        subchunk_outcomes = self.map_subchunks_to_outcome(spndx, chunks)

        return [subchunk_outcomes.get((subchunk_span.begin, subchunk_span.end), 'O') for subchunk_span, subchunk in subchunks]

    def create_chunks(self, spndx: Spandex, subchunks: Iterable[Annotation], outcomes: Iterable[str]):
        """
        attrib_func - function to parse tags and apply functions to output chunk type
        """
        chunks = []
        texts = [spndx.spanned_text(span) for span, _ in subchunks]
        prev_prefix = "O"
        prev_label = ""
        for text, subchunk, outcome in zip(texts, subchunks, outcomes):

            prefix, label = self.parse_outcome(outcome)

            if prefix != "O":
                if label != prev_label:
                    span = Span(begin=subchunk.begin, end=subchunk.end)
                    chunk = self.chunk_type()
                    self.attrib_func(chunk, outcome)
                    chunks.append((span, chunk))
                else:
                    chunk.end = subchunk.end
            else:
                chunk = None
            prev_prefix, prev_label = prefix, label

        spndx.add_layer(self.chunk_type, chunks)

    def map_subchunks_to_outcome(self, spndx: Spandex, chunks: Iterable[Annotation]):
        subchunk_outcomes = {}
        for chunk_span, chunk in chunks:
            for i, (subchunk_span, subchunk) in enumerate(spndx.covered(self.subchunk_type, chunk_span)):
                tag = 'B' if i == 0 else 'I'
                suffix = self.suffix_func(chunk)
                subchunk_outcomes[(subchunk_span.begin, subchunk_span.end)] = f"{tag}{suffix}"
        return subchunk_outcomes


    def merge_outcomes(self, outcomes1, outcomes2):

        status = 'O'
        merged = []
        for o1, o2 in zip(outcomes1, outcomes2):
            if status == 'O':
                if 'B' in [o1, o2]:
                    merged.append('B')
                    status = 'B'
                else:
                    merged.append('O')
                    status = 'O'

            elif status in ['B', 'I']:
                if 'B' in [o1, o2] or 'I' in [o1, o2]:
                    merged.append('I')
                    status = 'I'
                else:
                    merged.append('O')
                    status = 'O'
        return merged


class ChunkMetrics:

    def __init__(self, schema_annotation_map):
        self.schema_annotation_map = schema_annotation_map

        self. metrics_results = {
            'correct': 0, 'incorrect': 0, 'partial': 0,
            'missed': 0, 'spurious': 0, 'possible': 0, 'actual': 0
        }

        # overall results
        self.results_template = {
            'strict': deepcopy(self.metrics_results),
            'ent_type': deepcopy(self.metrics_results),
            'partial': deepcopy(self.metrics_results),
            'exact': deepcopy(self.metrics_results)
        }

        self.results = deepcopy(self.results_template)

        # results aggregated by entity type
        self.evaluation_agg_entities_type = {
            name: deepcopy(self.results_template) for name, _ in schema_annotation_map.items()
        }

    def find_overlap(self, actual_range, pred_range):
        """Find the overlap between two ranges
        Find the overlap between two ranges. Return the overlapping values if
        present, else return an empty set().
        Examples:
        >>> find_overlap((1, 2), (2, 3))
        2
        >>> find_overlap((1, 2), (3, 4))
        set()
        """

        actual_set = set(actual_range)
        pred_set = set(pred_range)

        overlaps = actual_set.intersection(pred_set)

        return overlaps

    def compute_actual_possible(self, results):
        """
        Takes a result dict that has been output by compute metrics.
        Returns the results dict with actual, possible populated.
        When the results dicts is from partial or ent_type metrics, then
        partial_or_type=True to ensure the right calculation is used for
        calculating precision and recall.
        """

        correct = results['correct']
        incorrect = results['incorrect']
        partial = results['partial']
        missed = results['missed']
        spurious = results['spurious']

        # Possible: number annotations in the gold-standard which contribute to the
        # final score

        possible = correct + incorrect + partial + missed

        # Actual: number of annotations produced by the NER system

        actual = correct + incorrect + partial + spurious

        results["actual"] = actual
        results["possible"] = possible

        return results

    

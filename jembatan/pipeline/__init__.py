from typing import Iterable

from jembatan.core.spandex import Spandex


class SimplePipeline:
    """
    Class wrapping common functions for processing document collections
    """

    @classmethod
    def iterate(cls, collection: Iterable[Spandex], stages: Iterable):
        """
        Process Spandex collection
        Iterator over processed Spandexes.  Useful if you want to work with the Spandex objects beyond just
        processing the pipeline.  This is one way to instrument collection of results for evaluation
        without putting it into your pipeline.

        """
        for spndx in collection:
            for stage in stages:
                stage.process(spndx)
            yield spndx

    @classmethod
    def iterate_by_stage(cls, collection: Iterable[Spandex], stages: Iterable):
        for i, spndx in enumerate(collection):
            path = []
            for stage in stages:
                path.append(str(stage))
                stage.process(spndx)
                yield i, '/'.join(path), spndx

    @classmethod
    def run(cls, collection: Iterable[Spandex], stages: Iterable):
        """
        Executes a linear pipeline of stages and runs collection_process_complete on those stages
        """
        for spndx in cls.iterate(collection, stages):
            pass

        for stage in stages:
            # allow annotators to do cleanup
            try:
                getattr(stage, 'collect_process_complete')
                stage.collection_process_complete()
            except AttributeError:
                pass

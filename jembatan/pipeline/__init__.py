import jembatan.spandex as spandex

class SpandexAnnotator(object):
    """
    Base annotator class for processing Spandex objects. This is provided as a convenience
    for object-oriented development of annotators.  By virtue of python duck-typing
    any function that accepts a Spandex object or any class that overrides 
    __call__(self, spndx) will work as well.
    """

    def process(self, spndx):
        """
        Override this method to define Annotator behavior.  Typically this is used to add
        annotation or data to the Spandex object.
        """
        pass


    def __call__(self, spndx):
        """ Processes Spandex object """
        self.process(spndx)


class AggregateSpandexAnnotator(SpandexAnnotator):
    """ A 'simple' class for pipelining annotators which serially process a Spandex object.

    Beyond simply passing the same Spandex between annotators, AggregateSpandexAnnotator
    has support for mapping of view names.  This allows annotators which operate in
    specific views to be reused on different views without need for re-instantiating or
    re-configuring the annotator.  A common use case is running tokenization on
    a Gold and Test view of the data.


    Usage:

        # for the sake of example assume:
        # 1. spandex has been initialized with text in views named "gold", "test" 
        # as well as the default view
        # 2. sentence_annotator is a function or functor that accepts and directly
        # manipulates the spandex it is given without retrieving other views

        # load/initialize spandex
        spndx = ...

        agg_pipeline = AggregateSpandexAnnotator()

        # annotate sentences on the default view
        agg_pipeline.add(sentence_annotator)

        # annotate sentences on the gold view
        agg_pipeline.add(sentence_annotator, {spandex.constants.SPANDEX_DEFAULT_VIEW: "gold"})

        # annotate sentences on the test view
        agg_pipeline.add(sentence_annotator, {spandex.constants.SPANDEX_DEFAULT_VIEW: "test"})

        # run the pipeline on a spandex doc
        agg_pipeline(spndx)

    """


    def __init__(self):
        """ create empty Aggregate Annotator 
        """
        self.annotators = []
        self.view_maps = []

    def add(self, annotator, view_map=None):
        """ Add annotator to pipeline

        Args:
        annotator (:obj:) a function or an object with __call__ '()' implemented.  
            An annotator accepts and processes a Spandex object

        view_map (dict, optional): A dictionary mapping between the views used internally
            by the annotator and the views present in the spandex.  Defaults of None
            indicates not to do mapping.
        """
        self.annotators.append(annotator)
        self.view_maps.append(view_map)


    def process(self, spndx):
        # Under the hood this aggregate annotator will wrap the Spandex object up
        # for consumption by the annotator.
        for annotator, view_map in zip(self.annotators, self.view_maps):
            if view_map:
                mapped_spndx = spandex.ViewMappedSpandex(spndx, view_map)
            else:
                mapped_spndx = spndx

            # Always pass the mapped default view into the annotator
            # This way functions/methods that just run on what is passed
            # can do so without having to call get_view themselves
            mapped_view = mapped_spndx.get_view(spandex.constants.SPANDEX_DEFAULT_VIEW)
            annotator(mapped_view)


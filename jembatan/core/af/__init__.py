from typing import Dict, Optional, Union
import jembatan.core.spandex as spandex

class AnalysisFunction(object):
    """
    Base annotator class for processing Spandex objects. This is provided as a convenience
    for object-oriented development of annotators.  By virtue of python duck-typing
    any function that accepts a Spandex object or any class that overrides 
    __call__(self, spndx) will work as well.
    """

    def process(self, spndx, **kwargs):
        """
        Override this method to define Annotator behavior.  Typically this is used to add annotation or data to the Spandex object.

        Args:
            spndx(:obj:`Spandex`) - Spandex object to process
            **kwargs - Arbitrary keyword arguments.  These are typically 
                defined per AnalysisFunction.  Use these to inject behavior
                changes that can not be accounted for during initialization
        """
        pass


    def __call__(self, spndx, **kwargs):
        """ Processes Spandex object.  In most cases this should not be 
        overridden.  Instead subclasses should override the `process` method.
        
        Args:
            spndx(:obj:`Spandex`) - Spandex object to process
            **kwargs - Arbitrary keyword arguments.  These are typically 
                defined per AnalysisFunction.  Use these to inject behavior
                changes that can not be accounted for during initialization
       
        """
        self.process(spndx, **kwargs)


class AggregateAnalysisFunction(AnalysisFunction):
    """ A 'simple' class for pipelining annotators which serially process a Spandex object.

    Beyond simply passing the same Spandex between annotators, 
    `AggregateAnalysisFunction` has support for mapping of view names.  
    This allows annotators which operate in specific views to be reused on 
    different views without need for re-instantiating or re-configuring 
    the annotator.  A common use case is running tokenization on
    a Gold and Test view of the data.

    Usage:

        # for the sake of example assume:
        # 1. spandex has been initialized with text in views named "gold", "test" 
        # as well as the default view
        # 2. sentence_annotator is a function or functor that accepts and directly
        # manipulates the spandex it is given without retrieving other views

        # load/initialize spandex
        spndx = ...

        agg_pipeline = AggregateAnalysisFunction()

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
        self.af_kwargs_list = []

    def add(self, analysis_func: AnalysisFunction, view_map:Optional[Dict[str, str]]=None, **kwargs):
        """ Add analysis function to pipeline

        Args:
            analysis func(:obj:) a function or an object with
                '__call__(spndx, **kwargs)' implemented.
                An analysis function accepts and processes a Spandex object
                view_map (dict, optional): A dictionary mapping between the 
                views used internally by the analysis function and the views present in 
                the spandex.  Defaults of None indicates not to do mapping.

            **kwargs: extra parameters to pass to analysis function.process() to allow 
                for change in runtime behavior separate from remapping of view 
                names.  These are intended to allow for reuse of components 
                without need to initialize a new object.
        """
        self.annotators.append(analysis_func)
        self.view_maps.append(view_map)
        self.af_kwargs_list.append(kwargs)

    def process(self, spndx, **kwargs):
        """
        Runs the aggregate analysis function (pipeline) defined through calls
        to the `add` method.

        Args:
            spndx (:obj:`Spandex`): Spandex object to process

            **kwargs: Arbitrary keyword arguments.  Not currently used
        """
        # Under the hood this aggregate annotator will wrap the Spandex object up
        # for consumption by the annotator.
        for step, (annotator, view_map, af_kwargs) in \
                enumerate(zip(self.annotators, self.view_maps, self.af_kwargs_list)):

            if view_map:
                mapped_spndx = spandex.ViewMappedSpandex(spndx, view_map)
            else:
                mapped_spndx = spndx

            # Always pass the mapped default view into the annotator
            # This way functions/methods that just run on what is passed
            # can do so without having to call get_view themselves
            try:
                mapped_view = mapped_spndx.get_view(spandex.constants.SPANDEX_DEFAULT_VIEW)
            except KeyError:
                mapped_view = mapped_spndx
            annotator(mapped_view, **af_kwargs)


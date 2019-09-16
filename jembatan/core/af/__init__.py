from functools import wraps
from typing import Dict, Optional, Union
import jembatan.core.spandex as spandex


def process_default_view(f):
    """
    For single-view analysis functions it's often easier to define manipulations in terms
    of the view/spandex object instead of having to get the view from the parent jem object
    """
    @wraps(f)
    def process_wrapper(self, jemdoc: spandex.JembatanDoc, *args, **kwds):
        spndx = jemdoc.default_view
        return f(self, spndx, **kwds)
    return process_wrapper


class AnalysisFunction(object):
    """
    Base annotator class for processing Spandex objects. This is provided as a convenience
    for object-oriented development of annotators.  By virtue of python duck-typing
    any function that accepts a Spandex object or any class that overrides
    __call__(self, spndx) will work as well.
    """

    def process(self, jemdoc: spandex.JembatanDoc, **kwargs):
        """
        Override this method to define Annotator behavior.  Typically this is used to add annotation or data to the
        Spandex object.

        Args:
            jemdoc(:obj:`JembatanDoc`) - JembatanDoc object to process
            **kwargs - Arbitrary keyword arguments.  These are typically
                defined per AnalysisFunction.  Use these to inject behavior
                changes that can not be accounted for during initialization
        """
        pass

    def __call__(self, jemdoc: spandex.JembatanDoc, **kwargs):
        """ Processes Spandex object.  In most cases this should not be 
        overridden.  Instead subclasses should override the `process` method.

        Args:
            jemdoc(:obj:`JembatanDoc`) - JembatanDoc object to process
            **kwargs - Arbitrary keyword arguments.  These are typically
                defined per AnalysisFunction.  Use these to inject behavior
                changes that can not be accounted for during initialization

        """
        self.process(jemdoc, **kwargs)


class AggregateAnalysisFunction(AnalysisFunction):
    """ A 'simple' class for orchestrating annotators which serially process a JembatanDoc object.

    Beyond simply passing the same JembatanDoc between annotators,
    `AggregateAnalysisFunction` has support for mapping of view names.
    This allows annotators which operate in specific views to be reused on
    different views without need for re-instantiating or re-configuring
    the annotator.  This allows for reuse of components that operate over specific view names.
    The most common use case is for running single view components, which process the default view
    on alternative views.

    Consider a tokenizer that runs on the default view. For our pipeline we actually need it to run
    on Gold and Test views of our JembatanDoc container.

    Usage:
        # for the sake of example assume:
        # 1. spandex has been initialized with text in views named "gold", "test".
        # 2. sentence_annotator is a single-view function or functor that accepts a jembatan and only
        #    manipulates the default view without retrieving other views

        # load/initialize jembatan
        jemdoc = ...

        agg_pipeline = AggregateAnalysisFunction()

        # annotate sentences on the default view
        agg_pipeline.add(sentence_annotator)

        # annotate sentences on the gold view
        agg_pipeline.add(sentence_annotator, {spandex.constants.SPANDEX_DEFAULT_VIEW: "gold"})

        # annotate sentences on the test view
        agg_pipeline.add(sentence_annotator, {spandex.constants.SPANDEX_DEFAULT_VIEW: "test"})

        # run the pipeline on a the jembatan doc
        agg_pipeline(jemdoc)

    """

    def __init__(self):
        """
        Create empty Aggregate Annotator
        """
        self.annotators = []
        self.view_maps = []
        self.af_kwargs_list = []

    def add(self, analysis_func: AnalysisFunction, view_map: Optional[Dict[str, str]]=None, **kwargs):
        """ Add analysis function to pipeline

        Args:
            analysis func(:obj:) a function or an object with
                '__call__(jemdoc, **kwargs)' implemented.
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

    def process(self, jemdoc: spandex.JembatanDoc, **kwargs):
        """
        Runs the aggregate analysis function (pipeline) defined through calls
        to the `add` method.

        Args:
            jemdoc (:obj:`Spandex`): JembatanDoc document object to process

            **kwargs: Arbitrary keyword arguments.  Not currently used
        """
        # Under the hood this aggregate annotator will wrap the Spandex object up
        # for consumption by the annotator.
        for step, (annotator, view_map, af_kwargs) in \
                enumerate(zip(self.annotators, self.view_maps, self.af_kwargs_list)):

            if view_map:
                mapped_jemdoc = spandex.ViewMappedJembatanDoc(jemdoc, view_map)
            else:
                mapped_jemdoc = jemdoc

            annotator(mapped_jemdoc, **af_kwargs)

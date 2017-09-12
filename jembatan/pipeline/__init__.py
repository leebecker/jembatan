class SpandexAnnotator(object):
    """
    Base annotator class for processing Spandex objects.
    """

    def on_pre_process(self, spndx):
        """ 
        Override this method to inject behavior prior to processing of the Spandex object.
        """
        pass

    def on_post_process(self, spndx):
        """
        Override this method to inject behavior after processing of the Spandex object.

        """
        pass

    def process(self, spndx):
        """
        Override this method to define Annotator behavior.  Typically this is used to add
        annotation or data to the Spandex object.
        """
        pass


    def __call__(self, spndx):
        """ Processes Spandex object """

        # TODO: Exception handling
        self.on_pre_process(spndx)

        # TODO: Exception handling
        self.on_post_process(spndx)


class AggregateSpandexAnnotator(SpandexAnnotator):
    """ A simple class for pipelining annotators which serially process a Spandex object. """
        
    def __init__(self, annotators=None):
        """ 
        Args:
            annotators: Iterable of annotators.  Annotators must be callable and accept a 
                Spandex object.  Defaults to None.
        """
        self.annotators = []
        if annotators:
            self.add(annotators)

    def add(self, annotators):
        """
        Add one or more annotators to the aggregate

        Args:
            annotators: Iterable of annotators.  Annotators must be callable and accept a 
                Spandex object.
        """
        for i, annotator in enumerate(annotators):
            if callable(annotator):
                self.annotators.append(annotator)
            else:
                raise TypeError("annotators[{:d}] ({}) is not callable.".format(i, annotator))

    def process(self, spndx):
        for f in self.annotators:
            f(spndx)


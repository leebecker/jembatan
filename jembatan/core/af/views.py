from jembatan.core.af import AnalysisFunction
from jembatan.core.spandex import JembatanDoc


class ViewCreator(AnalysisFunction):
    """ This annotator can be placed at/near the beginning of a pipeline to
    ensure that a particular view  is created before it is used further
    downstream. It will create a view for the view name specified at
    construction.  If it doesn't exist.

    One place this is useful is if you are using an annotator that uses the
    default view and you have mapped the default view into a different view
    via a mapping.  The default view is created automatically - but if you
    have mapped the default view to some other view, then the view provided to
    your annotator (when it asks for the default view) will not be created
    unless you have explicitly created it.
    """

    def process(self, jemdoc: JembatanDoc, viewname, **kwargs):
        self.create_view_safely(jemdoc, viewname)

    @classmethod
    def create_view_safely(cls, jemdoc: JembatanDoc, viewname: str):
        jemdoc.create_view(viewname)


class ViewTextCopier(AnalysisFunction):

    def process(self, jemdoc: JembatanDoc, src_viewname, tgt_viewname, **kwargs):
        srcview = jemdoc.get_view(src_viewname)
        tgtview = jemdoc.get_view(tgt_viewname)
        tgtview.content_string = srcview.content_string
        tgtview.content_mime = srcview.content_mime

from collections import namedtuple
from jembatan.core.af import AnalysisFunction

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

    def __init__(self, viewname):
        self.viewname = viewname

    def process(self, spndx):
        self.create_view_safely(spndx, self.viewname)

    @classmethod
    def create_view_safely(cls, spndx, viewname):
        spndx.create_view(viewname, None)
    

class ViewTextCopier(AnalysisFunction):
    Constants = namedtuple(
        "ViewTextCopierConstants", 
        ["DEFAULT_SOURCE_VIEW", "DEFAULT_TARGET_VIEW"])

    constants = Constants("_DEFAULT_SOURCE_VIEW", "_DEFAULT_TARGET_VIEW")

    def __init__(self, src_viewname=None, tgt_viewname=None):
        self.src_viewname = src_viewname if src_viewname else self.constants.DEFAULT_SOURCE_VIEW
        self.tgt_viewname = tgt_viewname if tgt_viewname else self.constants.DEFAULT_TARGET_VIEW

    def process(self, spndx):

        print ("ViewTextCopier", spndx)
        srcview = spndx[self.src_viewname]
        print ("\t src: {}".format(srcview))
        tgtview = spndx[self.tgt_viewname]
        print ("\t tgt: {}".format(tgtview))
        print ("tgtview.content: {}".format(tgtview.content))
        tgtview.content = srcview.content
        print ("tgtview.content: {}".format(tgtview.content))

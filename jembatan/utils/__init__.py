from jembatan.core.af import AnalysisFunction
from jembatan.core.spandex import Spandex


def copy_view(spndx: Spandex, src_viewname: str, tgt_viewname: str):
    src_view = spndx.get_view(src_viewname)
    tgt_view = spndx.get_or_create_view(tgt_viewname)

    tgt_view.content_string = src_view.content_string
    tgt_view.content_mime = src_view.content_mime

    return tgt_view


class ViewCopier(AnalysisFunction):
    """
    Wraps copy_view function in an AnalysisFunction
    """

    def __init__(self, src_viewname: str, tgt_viewname: str):
        self.src_viewname = src_viewname
        self.tgt_viewname = tgt_viewname

    def process(self, spndx):
        copy_view(spndx, self.src_viewname, self.tgt_viewname)

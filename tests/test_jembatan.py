from jembatan.core.spandex import JembatanDoc, ViewMappedJembatanDoc
from jembatan.core.spandex import constants as jemconst


def test_viewmapped_wrappers():
    default_view_content = "This is the default view content"
    jem = JembatanDoc(metadata="metadata", content_string=default_view_content)

    other_view_content = "This is the mapped default view content"
    other_viewname = "Other"
    other_view = jem.create_view(viewname=other_viewname, content_string=other_view_content)

    view_map = {
        jemconst.SPANDEX_DEFAULT_VIEW: other_viewname
    }

    mapped_jem = ViewMappedJembatanDoc(jem, view_map)

    assert other_view == jem.get_view(other_viewname)

    mapped_view = mapped_jem.get_view(jemconst.SPANDEX_DEFAULT_VIEW)
    assert other_view == mapped_view.wrapped

    assert other_view.content_string == mapped_view.content_string

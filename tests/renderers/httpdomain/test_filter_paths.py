import pytest

from sphinxcontrib.openapi import renderers


def textify(generator):
    return "\n".join(generator)


@pytest.mark.parametrize("options", [
    {"include": ["/included/.+"]},
    {"exclude": ["/excluded"]},
])
def test_filter_path_includes_paths(fakestate, oas_fragment, options):
    """Paths that match are included"""
    testrenderer = renderers.HttpdomainRenderer(fakestate, options)
    markup = textify(
        testrenderer.render_restructuredtext_markup(
            oas_fragment("""
            swagger: 3.0
            info:
              version: 1.0.0
              title: Some Title
            paths:
              /included/123:
                get:
                  name: included
                  responses: {}
              /excluded:
                get:
                  name: excluded
                  responses: {}
        """)
        )
    )
    assert ".. http:get:: /included/123" in markup
    assert ".. http:get:: /excluded" not in markup

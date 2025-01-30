from pathlib import Path
from typing import List

import pytest

from bs4 import BeautifulSoup, Tag
from sphinx.application import Sphinx
from sphinx.util.images import get_image_size
from sphinxcontrib.drawio import DrawIOError


@pytest.mark.sphinx("html", testroot="page-index")
def test_page_index(images: List[Path]):
    assert images[0].name == "pages.png"
    assert images[1].name == "pages1.png"
    assert images[2].name == "pages2.png"
    assert images[3].name == "pages.png"
    assert get_image_size(images[0]) == (125, 65)
    assert get_image_size(images[1]) == (65, 65)
    assert get_image_size(images[2]) == (65, 65)
    assert get_image_size(images[3]) == (125, 65)


@pytest.mark.sphinx("html", testroot="page-index-out-of-range")
def test_page_index_out_of_range(content: Sphinx, directives: List[Tag]):
    assert len(directives) == 1

    warnings = content._warning.getvalue()
    assert "selected page 6 is out of range [0,5]" in warnings


@pytest.mark.sphinx("html", testroot="page-name")
def test_page_name(images: List[Path]):
    assert images[0].name == "pages.png"
    assert images[1].name == "pages1.png"
    assert get_image_size(images[0]) == (125, 65)
    assert get_image_size(images[1]) == (65, 65)


@pytest.mark.sphinx("html", testroot="alt")
def test_alt(directives: List[Tag]):
    assert directives[0]["alt"] == "An Example"


@pytest.mark.sphinx("html", testroot="align")
def test_align(directives: List[Tag]):
    assert "align-left" in directives[0]["class"]
    assert "align-center" in directives[1]["class"]
    assert "align-right" in directives[2]["class"]


# noinspection PyTypeChecker
@pytest.mark.sphinx("html", testroot="width-height")
def test_width_height(images: List[Path]):
    assert get_image_size(images[0])[0] == 100
    assert get_image_size(images[1])[1] == 100
    assert get_image_size(images[2])[0] == 1000


# noinspection PyTypeChecker
@pytest.mark.sphinx("html", testroot="scale")
def test_scale(images: List[Path]):
    # image size by default is 125x65. the scaling isn't perfect
    assert get_image_size(images[0]) == (245, 125)
    assert get_image_size(images[1]) == (1217, 617)
    assert get_image_size(images[2]) == (64, 34)
    assert get_image_size(images[3]) == (125, 65)
    assert get_image_size(images[4]) == (610, 310)


@pytest.mark.skip(reason="No actual test case")
@pytest.mark.sphinx("html", testroot="transparency")
def test_transparency():
    pass


@pytest.mark.sphinx("html", testroot="image")
def test_image(directives: List[Tag]):
    (img,) = directives
    assert img.name == "img"
    assert img["src"] == "_images/box.svg"
    assert img["alt"] == "_images/box.svg"
    assert img["class"] == ["drawio"]


@pytest.mark.sphinx("html", testroot="figure")
def test_figure(content: Sphinx, directives: List[Tag]):
    filenames_sizes = [
        ("box.png", (125, 65)),
        ("box1.png", (185, 95)),
    ]
    for img, (filename, size) in zip(directives, filenames_sizes):
        assert img.name == "img"
        assert img["src"] == "_images/" + filename
        assert img["alt"] == "_images/" + filename
        assert img["class"] == ["drawio"]
        image_path = content.outdir / img["src"]
        assert get_image_size(image_path) == size
        imageContainerTag = img.parent
        assert imageContainerTag.name == "figure"


@pytest.mark.sphinx("html", testroot="reference")
def test_reference(directives: List[Tag]):
    (img,) = directives
    assert img.name == "img"
    assert img["src"] == "_images/box.svg"
    assert img["alt"] == "_images/box.svg"
    assert img["class"] == ["drawio"]


@pytest.mark.sphinx("html", testroot="warnings")
def test_warnings(content: Sphinx, directives: List[Tag]):
    assert len(directives) == 1
    warnings = content._warning.getvalue()
    assert "1 argument(s) required, 0 supplied" in warnings
    assert "image file not readable: missing.drawio" in warnings
    assert '"gif" unknown; choose from "png", "jpg", "svg", or "pdf".' in warnings


@pytest.mark.sphinx("html", testroot="bad-config")
def test_bad_config(app_with_local_user_config):
    with pytest.raises(DrawIOError) as exc:
        app_with_local_user_config.build()
    (message,) = exc.value.args
    assert message == "export format 'bmp' is unsupported by draw.io"


@pytest.mark.sphinx("html", testroot="bad-config2")
def test_bad_config2(app_with_local_user_config):
    with pytest.raises(DrawIOError) as exc:
        app_with_local_user_config.build()
    (message,) = exc.value.args
    assert message == "invalid export format 'pdf' specified for builder 'html'"


@pytest.mark.sphinx("html", testroot="page-name-not-exist")
def test_page_name_not_exist_config(app_with_local_user_config):
    with pytest.raises(DrawIOError) as exc:
        app_with_local_user_config.build()
    (message,) = exc.value.args
    assert "has no diagram named: none existed page name" in message


@pytest.mark.sphinx("html", testroot="page-name-and-page-index")
def test_page_name_and_page_index_config(app_with_local_user_config):
    with pytest.raises(DrawIOError) as exc:
        app_with_local_user_config.build()
    (message,) = exc.value.args
    assert message == "page-name & page-index cannot coexist"


@pytest.mark.sphinx("html", testroot="layer-selection")
def test_layer_selection(images: List[Path]):
    assert images[0].name == "layers.png"
    assert images[1].name == "layers1.png"
    assert images[2].name == "layers2.png"
    assert images[3].name == "layers3.png"
    assert images[4].name == "layers4.png"
    assert get_image_size(images[0]) == (125, 65)
    assert get_image_size(images[1]) == (65, 65)
    assert get_image_size(images[2]) == (105, 95)
    assert get_image_size(images[3]) == (125, 215)
    assert get_image_size(images[4]) == (125, 125)

@pytest.mark.sphinx("html", testroot="svg-theme")
def test_svg_theme(images: List[Path]):
    # Image settings:
    #  index.rst image 1 (=auto)
    #  index.rst image 2 (=light)
    #  index.rst image 3 (=dark)
    #  index.rst image 4 (=conf.py default setting, i.e. light)
    expected_color_schemes = ["light dark", "light", "dark", "light"]

    for i, image in enumerate(images):
        content = image.read_text()
        svg_tag = BeautifulSoup(content, 'xml').find('svg')
        style_value = svg_tag['style']
        assert f"color-scheme: {expected_color_schemes[i]};" in style_value

@pytest.mark.sphinx("html", testroot="layer-not-exist")
def test_layer_not_exist(app_with_local_user_config):
    with pytest.raises(DrawIOError) as exc:
        app_with_local_user_config.build()
    (message,) = exc.value.args
    assert "Export failed" in message




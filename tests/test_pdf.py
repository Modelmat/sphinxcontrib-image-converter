import re
import sphinx
from pathlib import Path
from typing import List

import pytest


def mediabox_rough_equal(a: (float, float), b: (float, float), max_diff: float = 2.0) -> bool:
    ((a_width, a_height), (b_width, b_height)) = (a, b)
    return abs(a_height - b_height) <= max_diff and abs(a_width - b_width) <= max_diff


@pytest.mark.sphinx("latex", testroot="image", srcdir="pdf_image")
def test_pdf_image(tex_images: List[Path]):
    (image,) = tex_images
    if sphinx.version_info[:2] < (7, 2):
        assert image.basename() == "box.pdf"
    else:
        assert image.name == "box.pdf"


@pytest.mark.sphinx("latex", testroot="image", srcdir="pdf_image_crop")
def test_pdf_image_crop(tex_images: List[Path]):
    (image,) = tex_images
    mediabox = tuple(map(float, get_mediabox(image)))
    assert mediabox_rough_equal(mediabox, (88.080002, 47.039997))


RE_MEDIABOX = re.compile(rb"^/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]")


def get_mediabox(filename):
    with filename.open("rb") as pdf:
        for line in pdf.readlines():
            m = RE_MEDIABOX.match(line)
            if m:
                break
        else:
            assert False, "Could not find MediaBox in exported PDF"
    return tuple(g.decode("ascii") for g in m.groups())

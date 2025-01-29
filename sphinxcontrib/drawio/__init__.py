import os
import os.path
import platform
import shutil
import subprocess
from hashlib import sha1
from pathlib import Path
from subprocess import Popen, PIPE
from tempfile import TemporaryFile
from time import sleep
from typing import Dict, Any, List
from xml.etree import ElementTree as ET

from docutils import nodes
from docutils.nodes import Node, image as docutils_image
from docutils.parsers.rst import directives
from docutils.parsers.rst.directives.images import Image
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.config import Config, ENUM
from sphinx.directives.patches import Figure
from sphinx.errors import SphinxError
from sphinx.transforms.post_transforms.images import ImageConverter, get_filename_for
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from sphinx.util.fileutil import copy_asset

__version__ = "0.0.17"

logger = logging.getLogger(__name__)

VALID_OUTPUT_FORMATS = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "svg": "image/svg+xml",
    "pdf": "application/pdf",
}

VALID_SVG_THEMES = ['auto', 'light', 'dark']

def is_headless(config: Config):
    if config.drawio_headless == "auto":
        if platform.system() != "Linux":
            # Xvfb can only run on Linux
            return False
        # DISPLAY will exist if an X-server is running
        return False if os.getenv("DISPLAY") else True
    elif isinstance(config.drawio_headless, bool):
        return config.drawio_headless
    # We should never reach this point as Sphinx ensures the config options


class DrawIOError(SphinxError):
    category = "DrawIO Error"


def format_spec(argument: Any) -> str:
    return directives.choice(argument, list(VALID_OUTPUT_FORMATS.keys()))

def svg_theme_spec(argument: Any) -> str:
    return directives.choice(argument, VALID_SVG_THEMES)

def is_valid_format(format: str, builder: Builder) -> str:
    mimetype = VALID_OUTPUT_FORMATS.get(format, None)

    if format is None:
        return None
    elif mimetype is None:
        raise DrawIOError(f"export format '{format}' is unsupported by draw.io")
    elif mimetype not in builder.supported_image_types:
        raise DrawIOError(
            f"invalid export format '{format}' specified for builder '{builder.name}'"
        )
    else:
        return format


def boolean_spec(argument: Any) -> bool:
    if argument == "true":
        return True
    elif argument == "false":
        return False
    else:
        raise ValueError("unexpected value. true or false expected")


def traverse(nodes):
    for node in nodes:
        yield node
        yield from traverse(node.children)


class DrawIOBase(SphinxDirective):
    option_spec = {
        "format": format_spec,
        "page-index": directives.nonnegative_int,
        "page-name": directives.unchanged,
        "transparency": boolean_spec,
        "export-scale": directives.positive_int,
        "export-width": directives.positive_int,
        "export-height": directives.positive_int,
        "layer-selection": directives.unchanged,
        "svg-theme": svg_theme_spec,
    }

    def run(self) -> List[Node]:
        nodes = super().run()
        for node in traverse(nodes):
            if isinstance(node, docutils_image):
                image = node
                break
        image["classes"].append("drawio")
        return nodes


class DrawIOImage(DrawIOBase, Image):
    option_spec = Image.option_spec.copy()
    option_spec.update(DrawIOBase.option_spec)


class DrawIOFigure(DrawIOBase, Figure):
    option_spec = Figure.option_spec.copy()
    option_spec.update(DrawIOBase.option_spec)


OPTIONAL_UNIQUES = {
    "export-height": "height",
    "export-width": "width",
}


class DrawIOConverter(ImageConverter):
    conversion_rules = [
        # automatic conversion based on the builder's supported image types
        ("application/x-drawio", "image/png"),
        ("application/x-drawio", "image/jpeg"),
        ("application/x-drawio", "image/svg+xml"),
        ("application/x-drawio", "application/pdf"),
        # when the export format is explicitly defined
        ("application/x-drawio-png", "image/png"),
        ("application/x-drawio-jpg", "image/jpeg"),
        ("application/x-drawio-svg", "image/svg+xml"),
        ("application/x-drawio-pdf", "application/pdf"),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        format = self.config.drawio_builder_export_format.get(self.app.builder.name)

        self._default_export_format = is_valid_format(format, self.app.builder)

    @property
    def imagedir(self) -> str:
        return os.path.join(self.app.doctreedir, "drawio")

    def is_available(self) -> bool:
        """Confirms the converter is available or not."""
        return True

    def guess_mimetypes(self, node: nodes.image) -> List[str]:
        if "drawio" in node["classes"]:
            node_format = is_valid_format(node.get("format"), self.app.builder)
            format = node_format or self._default_export_format
            extra = f"-{format}" if format else ""
            return ["application/x-drawio" + extra]
        else:
            return []

    def handle(self, node: nodes.image) -> None:
        """Render drawio file into an output image file."""
        _from, _to = self.get_conversion_rule(node)

        if _from in node["candidates"]:
            srcpath = node["candidates"][_from]
        else:
            srcpath = node["candidates"]["*"]

        abs_srcpath = Path(self.app.srcdir) / srcpath
        if not os.path.exists(abs_srcpath):
            return

        options = node.attributes
        out_filename = get_filename_for(srcpath, _to)
        destpath = str(self._drawio_export(abs_srcpath, options, out_filename))
        if "*" in node["candidates"]:
            node["candidates"]["*"] = destpath
        else:
            node["candidates"][_to] = destpath
        node["uri"] = destpath

        self.env.original_image_uri[destpath] = srcpath
        self.env.images.add_file(self.env.docname, destpath)

    @staticmethod
    def page_name_to_index(input_abspath: str, name: str):
        if name is None:
            return None

        for index, diagram in enumerate(ET.parse(input_abspath).getroot()):
            if diagram.tag != "diagram":
                continue
            if diagram.attrib["name"] == name:
                return index

        raise DrawIOError(f"draw.io file {input_abspath} has no diagram named: {name}")

    @staticmethod
    def num_pages_in_file(input_abspath: Path) -> int:
        # Each diagram/page is a direct child of the root element
        return len(ET.parse(input_abspath).getroot())

    def _drawio_export(self, input_abspath, options, out_filename):
        builder = self.app.builder
        input_relpath = input_abspath.relative_to(builder.srcdir)
        input_stem = input_abspath.stem

        page_name = options.get("page-name", None)
        page_index = options.get("page-index", None)
        if page_name is not None and page_index is not None:
            raise DrawIOError("page-name & page-index cannot coexist")

        if page_name:
            page_index = self.page_name_to_index(input_abspath, page_name)
        elif page_index:
            max_index = self.num_pages_in_file(input_abspath) - 1
            if page_index > max_index:
                logger.warning(
                    f"selected page {page_index} is out of range [0,{max_index}]"
                )
        elif page_index is None:
            page_index = 0

        page_index = str(page_index)

        scale = str(
            options.get("export-scale", builder.config.drawio_default_export_scale)
            / 100
        )
        transparent = options.get(
            "transparency", builder.config.drawio_default_transparency
        )
        layer_selection = options.get("layer-selection", None)
        disable_verbose_electron = builder.config.drawio_disable_verbose_electron
        disable_dev_shm_usage = builder.config.drawio_disable_dev_shm_usage
        disable_gpu = builder.config.drawio_disable_gpu
        no_sandbox = builder.config.drawio_no_sandbox
        svg_theme = options.get("svg-theme", builder.config.drawio_default_svg_theme)

        # Any directive options which would change the output file would go here
        unique_values = (
            # This ensures that the same file hash is generated no matter the build directory
            # Mainly useful for pytest, as it creates a new build directory every time
            str(input_relpath),
            page_index,
            str(layer_selection) if layer_selection else "",
            scale,
            "true" if transparent else "false",
            *[str(options.get(option)) for option in OPTIONAL_UNIQUES],
        )
        hash_key = "\n".join(unique_values)
        sha_key = sha1(hash_key.encode()).hexdigest()
        export_abspath = Path(self.imagedir) / sha_key / out_filename
        export_abspath.parent.mkdir(parents=True, exist_ok=True)
        export_relpath = export_abspath.relative_to(builder.doctreedir)
        output_format = export_abspath.suffix[1:]

        if (
            export_abspath.exists()
            and export_abspath.stat().st_mtime > input_abspath.stat().st_mtime
        ):
            return export_abspath

        drawio_in_path = shutil.which("drawio")
        draw_dot_io_in_path = shutil.which("draw.io")
        WINDOWS_PATH = r"C:\Program Files\draw.io\draw.io.exe"
        MACOS_PATH = "/Applications/draw.io.app/Contents/MacOS/draw.io"
        LINUX_PATH = "/opt/drawio/drawio"
        LINUX_OLD_PATH = "/opt/draw.io/drawio"

        if builder.config.drawio_binary_path:
            binary_path = builder.config.drawio_binary_path
        elif drawio_in_path:
            binary_path = drawio_in_path
        elif draw_dot_io_in_path:
            binary_path = draw_dot_io_in_path
        elif platform.system() == "Windows" and os.path.isfile(WINDOWS_PATH):
            binary_path = WINDOWS_PATH
        elif platform.system() == "Darwin" and os.path.isfile(MACOS_PATH):
            binary_path = MACOS_PATH
        elif platform.system() == "Linux" and os.path.isfile(LINUX_PATH):
            binary_path = LINUX_PATH
        elif platform.system() == "Linux" and os.path.isfile(LINUX_OLD_PATH):
            binary_path = LINUX_OLD_PATH
        else:
            raise DrawIOError("No drawio executable found")

        scale_args = ["--scale", scale]
        if output_format == "pdf" and float(scale) == 1.0:
            # https://github.com/jgraph/drawio-desktop/issues/344 workaround
            # This is fixed now, but is left in for backwards compat.
            scale_args.clear()

        extra_args = []
        for option, drawio_arg in OPTIONAL_UNIQUES.items():
            if option in options:
                value = options[option]
                extra_args.append(f"--{drawio_arg}")
                extra_args.append(str(value))

        if transparent:
            extra_args.append("--transparent")

        if layer_selection:
            extra_args.append("--layers")
            extra_args.append(layer_selection)

        drawio_args = [
            binary_path,
            "--export",
            "--crop",
            "--page-index",
            page_index,
            *scale_args,
            *extra_args,
            "--format",
            output_format,
            "--output",
            str(export_abspath),
            str(input_abspath),
        ]

        if not disable_verbose_electron:
            drawio_args.append("--enable-logging")

        if disable_dev_shm_usage:
            drawio_args.append("--disable-dev-shm-usage")

        if disable_gpu:
            drawio_args.append("--disable-gpu")
            drawio_args.append("--disable-software-rasterizer")
            drawio_args.append("--disable-features=DefaultPassthroughCommandDecoder")

        if no_sandbox:
            # This may be needed for docker support, and it has to be the last argument to work.
            drawio_args.append("--no-sandbox")

        if svg_theme:
            drawio_args.append("--svg-theme")
            drawio_args.append(svg_theme)

        new_env = os.environ.copy()
        if builder.config._display:
            new_env["DISPLAY"] = f":{builder.config._display}"

        # This environment variable prevents the drawio application from starting.
        # This is automatically set within certain Visual Studio Code contexts,
        # such as for the reStructuredText (sphinx) preview.
        new_env.pop("ELECTRON_RUN_AS_NODE", None)

        logger.info(f"(drawio) '{input_relpath}' -> '{export_relpath}'")
        try:
            ret = subprocess.run(
                drawio_args, stderr=PIPE, stdout=PIPE, check=True, env=new_env
            )
        except OSError as exc:
            raise DrawIOError(
                "draw.io ({args}) exited with error:\n{exc}".format(
                    args=" ".join(drawio_args), exc=exc
                )
            )
        except subprocess.CalledProcessError as exc:
            raise DrawIOError(
                "draw.io ({args}) exited with error:\n[stderr]\n{stderr}"
                "\n[stdout]\n{stdout}\n[returncode]\n{returncode}".format(
                    args=" ".join(drawio_args),
                    stderr=exc.stderr,
                    stdout=exc.stdout,
                    returncode=exc.returncode,
                )
            )
        if not export_abspath.exists():
            raise DrawIOError(
                "draw.io ({args}) did not produce an output file:"
                "\n[stderr]\n{stderr}\n[stdout]\n{stdout}".format(
                    args=" ".join(drawio_args), stderr=ret.stderr, stdout=ret.stdout
                )
            )
        return export_abspath


def on_config_inited(app: Sphinx, config: Config) -> None:
    if is_headless(config):
        logger.info("running in headless mode, starting Xvfb")
        with TemporaryFile() as fp:
            fd = fp.fileno()
            xvfb = Popen(
                ["Xvfb", "-displayfd", str(fd), "-screen", "0", "1280x768x16"],
                pass_fds=(fd,),
                stdout=PIPE,
                stderr=PIPE,
            )
            if xvfb.poll() is not None:
                raise OSError(
                    f"Failed to start Xvfb process"
                    "\n[stdout]\n{}\n[stderr]{*xvfb.communicate()}"
                )
            while fp.tell() == 0:
                sleep(0.01)  # wait for Xvfb to start up
            fp.seek(0)
            config._xvfb = xvfb
            config._display = fp.read().decode("ascii").strip()
        logger.info(f"Xvfb is running on display :{config._display}")
    else:
        logger.info("running in non-headless mode, not starting Xvfb")
        config._xvfb = None
        config._display = None


def on_build_finished(app: Sphinx, exc: Exception) -> None:
    if app.builder.format == 'html' and exc is None:
        this_file_path = os.path.dirname(os.path.realpath(__file__))
        src = os.path.join(this_file_path, "drawio.css")
        dst = os.path.join(app.outdir, "_static")
        copy_asset(src, dst)

    if app.config._xvfb:
        app.config._xvfb.terminate()
        stdout, stderr = app.config._xvfb.communicate()
        if app.config._xvfb.poll() != 0:
            raise OSError(
                f"Encountered an issue while terminating Xvfb"
                "\n[stdout]\n{stdout}\n[stderr]{stderr}"
            )


def setup(app: Sphinx) -> Dict[str, Any]:
    app.add_post_transform(DrawIOConverter)
    app.add_directive("drawio-image", DrawIOImage)
    app.add_directive("drawio-figure", DrawIOFigure)
    app.add_config_value("drawio_builder_export_format", {}, "html", dict)
    app.add_config_value("drawio_default_export_scale", 100, "html")
    # noinspection PyTypeChecker
    app.add_config_value(
        "drawio_default_transparency", False, "html", ENUM(True, False)
    )
    app.add_config_value("drawio_binary_path", None, "html")
    # noinspection PyTypeChecker
    app.add_config_value("drawio_headless", "auto", "html", ENUM("auto", True, False))
    # noinspection PyTypeChecker
    app.add_config_value(
        "drawio_disable_verbose_electron", False, "html", ENUM(True, False)
    )
    app.add_config_value(
        "drawio_disable_dev_shm_usage", False, "html", ENUM(True, False)
    )
    app.add_config_value("drawio_disable_gpu", False, "html", ENUM(True, False))
    app.add_config_value("drawio_no_sandbox", False, "html", ENUM(True, False))
    app.add_config_value("drawio_default_svg_theme", "auto", "html", ENUM(*VALID_SVG_THEMES))

    # Add CSS file to the HTML static path for add_css_file
    app.connect("build-finished", on_build_finished)
    app.connect("config-inited", on_config_inited)
    app.add_css_file("drawio.css")

    return {"version": __version__, "parallel_read_safe": True}

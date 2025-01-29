# sphinxcontrib-drawio

Sphinx Extension adding the `drawio-image` and `drawio-figure` directives.
These are equivalent to the standard `image` and `figure` directives, but
accept the path to a `.drawio` file and additional options to control
exporting of the diagram to a suitable image format. 

**Important:** This extension does not work on readthedocs as RTD does not allow
packages (e.g. drawio) to be installed. If you only require diagrams in a single
format, you can consider using editable SVGs or PNGs, accessible through
draw.io's File > Export menu.

The drawio-desktop package does not run without an x-server (e.g. when in a CI
environment), see [this issue](https://github.com/jgraph/drawio-desktop/issues/146).
The workaround is to install `xvfb` and set the `drawio_headless` configuration
option to `auto`.

If any other of the `draw.io` CLI tool's options are wanted, please file an
issue.

## Installation

1. `python3 -m pip install sphinxcontrib-drawio`
2. In your sphinx config, add:

    ```python
    extensions = [
        "sphinxcontrib.drawio"
    ]
    ```

3. Add the draw.io binary to `$PATH`. See [Options: Binary Path](#binary-path)
   for more details and alternative solutions.

4. If running headless, install Xvfb, e.g. via `$ sudo apt install xvfb`.

## Options
These values are placed in the `conf.py` of your sphinx project.

### Binary Path
- *Formal Name*: `drawio_binary_path`
- *Default Value*: `None`

This allows for a specific override for the binary location. By default, this
chooses the `drawio` (or `draw.io.exe`) binary accessible in `$PATH`. However,
if this file does not exist, it picks the platform-appropriate path:

- Windows: `C:\Program Files\draw.io\draw.io.exe`
- Linux: `/opt/drawio/drawio` or `/opt/draw.io/drawio` (older versions)
- MacOS: `/Applications/draw.io.app/Contents/MacOS/draw.io`.

### Headless Mode
- *Formal Name*: `drawio_headless`
- *Default Value*: `"auto"`
- *Possible Values*: `True`, `False`, or `"auto"`

This config option controls the behaviour of running the Xvfb server. It is
necessary because `draw.io` will not work without an X-server, see
[this issue](https://github.com/jgraph/drawio-desktop/issues/146).

The `auto` mode will detect whether the program is running in a headless
environment through the `$DISPLAY` environment variable, and act as if it were
set to `True`. If not running on Linux, or the `$DISPLAY` environment variable
contains some value (i.e. running in an X-server on a developer's machine), it
will act as it it were set to `False`.

Setting the value to `True` will start a virtual X framebuffer through the
`Xvfb` command before running any `draw.io` commands, and stop it afterwards.

Setting the value to `False` will run the `draw.io` binary as normal.

### Default Output Format
- *Formal Name*: `drawio_builder_export_format`
- *Default Value*: `{}`

This config option controls the default export file format for each Sphinx
builder. It accepts a dictionary mapping builder names to image formats. The
builder name should match the name of a [Sphinx builder](https://www.sphinx-doc.org/en/master/usage/builders/index.html)
(e.g., `"html"`, `"latex"`). Accepted values for the export format are `"png"`,
`"jpg"`, `"svg"` and `"pdf"`. If no format is set for a given builder, its
preferred image format is used, that is, the first format listed in a builder's
_supported_image_types_ that draw.io is capable of exporting to (eg. SVG for
HTML, PDF for LaTeX). 

### Default Export Scale
- *Formal Name*: `drawio_default_export_scale`
- *Default Value*: `100`
- *Possible Values*: any positive integer

This config option sets the default export scale for all diagrams. This scales
the size of the diagram. So if you take a diagram that by default would output 
a image with a resolution of 50x50 pixels and a scale of 200, you will obtain an
image with a resolution that is approximately 100x100 pixels. By default draw.io
*usually* outputs relatively low resolution images, so this setting can be used
to remedy that. 

This setting will get automatically overridden if the `scale` is set for a
individual diagram in the directive. If either `export-width` or `export-height`
are set for an image, this option will have no effect on the generated image.

### Default Transparency
- *Formal Name*: `drawio_default_transparency`
- *Default Value*:  `False`
- *Possible Values*: `True` or `False`

This changes the background transparency for diagrams exported in *png* format. 
This will be overridden if the transparency is set for a individual diagram in
the directive. If the output format isn't *png*, it will not affect the image
exported.

### Disable Verbose Electron
- *Formal Name*: `drawio_disable_verbose_electron`
- *Default Value*: `False`
- *Possible Values*: `True` or `False`

Electron's verbose logging is turned on by default to help troubleshoot certain
errors produced by the drawio app, but can be disabled if it causes a logging
conflict. This option only affects the output when the drawio app errors. See the
[Electron docs](https://www.electronjs.org/docs/latest/api/command-line-switches#--enable-loggingfile)
for more info.

### Disable Shared Memory Usage
- *Formal Name*: `drawio_disable_dev_shm_usage`
- *Default Value*: `False`
- *Possible Values*: `True` or `False`

By default, Docker runs a container with a `/dev/shm` shared memory space of 64MB.
This is typically too small for Chrome (Electron) and will cause Chrome to throw
an error. Launching the browser with the `--disable-dev-shm-usage` flag will write
shared memory files into `/tmp` instead of `/dev/shm`.

### Disable GPU
- *Formal Name*: `drawio_disable_gpu`
- *Default Value*: `False`
- *Possible Values*: `True` or `False`

By default, Chrome (Electron) uses GPU processes which can cause errors when
running in environments that are not set up for it. This option disables those
GPU processes and uses the CPU instead.

### No Sandbox
- *Formal Name*: `drawio_no_sandbox`
- *Default Value*: `False`
- *Possible Values*: `True` or `False`

This option may be needed to work in a docker container. You should probably
only enable it if you are experiencing issues. See https://github.com/jgraph/drawio-desktop/issues/144 
for more info. 

### SVG theme
- *Formal Name*: `drawio_default_svg_theme`
- *Default Value*: `"auto"`
- *Possible Values*: `"auto"`, `"light"`, `"dark"`

This option controls the adaptive color theming for SVG files.
When set to "auto", SVG files will be rendered with a color scheme that fits
to the user's desktop theme: the SVG will be rendered with a dark/light color scheme
when the desktop theme is set to a "dark"/"light" theme.
In some cases, it might be desirable to force SVG files to always be rendered
with "light" or "dark" color schemes. This can be done by setting this option
to either value.

## Usage
The extension can be used through the `drawio-image` directive. For example:
```
.. drawio-image:: example.drawio
   :export-scale: 150
```

There's also a `drawio-figure` directive that mimics the `figure` directive:
```
.. drawio-figure:: example.drawio
   :format: png

   An example diagram
```

The directives can be configured with options to control the export of the
draw.io diagram to a bitmap or vector image. These options are documented below.

Additionally, `drawio-image` accepts all of the options supported by the
[image directive](https://docutils.sourceforge.io/docs/ref/rst/directives.html#image).
These options apply to the image as exported by draw.io. Similarly,
`drawio-figure` accepts all options supported by the [figure directive](https://docutils.sourceforge.io/docs/ref/rst/directives.html#figure).

### Format
- *Formal Name*: `:format:`
- *Default Value*: `"png"`
- *Possible Values*: `"png"`, `"jpg"`, `"svg"` or `"pdf"`

This option controls the output file format of *this specific* directive.

### Page Index
- *Formal Name*: `:page-index:`
- *Default Value*: `0`
- *Possible Values*: any integer

This option allows you to select a particular page from a draw.io file to
export. Note that an invalid page-index will revert to one of the other valid
pages (draw.io binary functionality). `page-name` and `page-index` cannot
coexist, if you set both options, an error will be reported.

### Page Name
- *Formal Name*: `:page-name:`
- *Default Value*: value of `:page-index:`, else the first page
- *Possible Values*: any string

This option allows you to select a particular page by its name from a draw.io
file to export. `page-name` and `page-index` cannot coexist, if you set both
options, an error will be reported. If `:page-name:` is not found in the draw.io
file, an error will be reported too.

### Export Scale
- *Formal Name*: `:export-scale:`
- *Default Value*: `drawio_default_export_scale` set in conf.py
- *Possible Values*: any positive integer

This scales the size of the output image. So if you take a diagram that by
default would output a image with a resolution of 50x50 pixels and a scale of
200, you will obtain an image with a resolution that is approximately 100x100 
pixels. By default draw.io *usually* outputs relatively low-resolution images,
so this setting can be used to remedy that. This overrides the
`drawio_default_export_scale` set in conf.py for this specific diagram. If
either `export-width` or `export-height` are set for a given image,
`export-scale` will have no effect on the generated image.

### Export Width
- *Formal Name*: `:export-width:`
- *Possible Values*: any positive integer

This fits the generated image into the specified width, preserving aspect ratio.
When exporting to a bitmap image, this specifies the width in pixels. For PDF,
a value of 100 corresponds to 1.00 inches.

### Export Height
- *Formal Name*: `:export-height:`
- *Possible Values*: any positive integer

This fits the generated image into the specified height, preserving aspect
ratio. When exporting to a bitmap image, this specifies the height in pixels.
For PDF, a value of 100 corresponds to 1.00 inches.

### Transparency
- *Formal Name*: `:transparency:`
- *Default Value*: `drawio_default_transparency` set in conf.py
- *Possible Values*: `"true"` or `"false"`

This changes the background transparency for diagrams exported to `png` files.
Will override `drawio_default_transparency` which was set in conf.py for this
specific diagram. If this setting is specified while the output format is not
`png` it will have no effect on the generated image

### Layer Selection
- *Formal Name*: `:layer-selection:`
- *Possible Values*: comma separated list of integers

This option allows you to select one or more layers from a draw.io file to
export. Note that draw.io uses 0 as the lowest layer, which is usually the
*Background* layer.
If not specified, all visible layers will be exported (draw.io binary functionality).

### SVG theme
- *Formal Name*: `:svg-theme:`
- *Default Value*: `drawio_default_svg_theme` set in conf.py
- *Possible Values*: `"auto"`, `"light"`, `"dark"`

This changes the adaptive color scheming used when rendering SVG files.
To make SVG files render according to the viewer's desktop theme, select `"auto"`.
To force SVG files to be rendered with light/dark color schemes, select `"light"`/`"dark"`.


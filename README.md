# web-compile

[![PyPI][pypi-badge]][pypi-link]

A CLI to compile/minify SCSS & JS, and associated pre-commit hook.

This CLI is a small wrapper around [libsass-python](https://github.com/sass/libsass-python),
[rJSmin](http://opensource.perlig.de/rjsmin/) and [jinja2](https://jinja.palletsprojects.com),
which also aims to be compatible with [pre-commit](https://pre-commit.com/),
and provide a pre-commit hook.

**NOTE**: The package in on alpha release, but looks to be working as intended,
and will be trialled in [sphinx-panels](https://github.com/executablebooks/sphinx-panels),
and then [sphinx-book-theme](https://github.com/executablebooks/sphinx-book-theme).

[pypi-badge]: https://img.shields.io/pypi/v/web-compile.svg
[pypi-link]: https://pypi.org/project/web-compile

## Installation

To use directly as a CLI:

```console
pip install web-compile
web-compile --help
```

To use *via* pre-commit:

Add to your `.pre-commit-config.yaml`

```yaml
-   repo: https://github.com/executablebooks/web-compile
    rev: v0.2.0
    hooks:
      - id: web-compile
        # optional
        args: [--config=config.yml]
        files: >-
            (?x)^(
                web-compile-config.yml|
                src/.*|
                dist/.*
            )$
```

By default, the hook will be initiated for all text file changes.
But it is advisable to constrain this to the known configuration file, and input/output folders.

## Configuration

You can can configure the compilation directly *via* the CLI or using a configuration file;
simply replace `-` with `_`, CLI takes priority over the file:

```console
$ web-compile --help
Usage: web-compile [OPTIONS]

  Compile web assets.

Options:
  --version                       Show the version and exit.
  -c, --config FILE               Allowed extensions: json, toml, yml, yaml
                                  [default: web-compile-config.yml]

  --sass-files DICT               File mapping (config only)
  --sass-format [nested|expanded|compact|compressed]
                                  [default: compressed]
  --sass-precision INTEGER        precision for numbers.  [default: 5]
  --sass-sourcemap                Output source map.
  --sass-encoding TEXT            [default: utf8]
  --js-files DICT                 File mapping (config only)
  --js-comments                   Keep comments starting with '/*!'.
  --js-encoding TEXT              [default: utf8]
  --jinja-files DICT              File mapping (config only)
  --jinja-variables DICT          Global variable mapping (config only)
  --jinja-encoding TEXT           [default: utf8]
  --git-add / --no-git-add        Add new files to git index.  [default: True]
  --continue-on-error             Do not stop on the first error.
  --exit-code INTEGER             Exit code when files changed.  [default: 3]
  --test-run                      Do not delete/create any files.
  -q, --quiet                     Remove stdout logging.
  -v, --verbose                   Increase stdout logging.
  --help                          Show this message and exit.
```

`--config` can point to any of three file-formats:

`config.yml`/`config.yaml`:

```yaml
web-compile:
  sass:
    encoding: utf8
    files:
      tests/example_src/example1.scss: tests/example_dist/example1.[hash].css
      tests/example_src/example2.scss: tests/example_dist/example2.[hash].css
    format: compressed
    precision: 5
    sourcemap: true
  js:
    comments: false
    encoding: utf8
    files:
      tests/example_src/example1.js: tests/example_dist/example1.[hash].js
  jinja:
    files:
      tests/example_src/example1.j2: tests/example_dist/example1.txt
      tests/example_src/example3.j2: tests/example_dist/example3.txt
    variables:
      a: b
  continue_on_error: true
  exit_code: 2
  test_run: false
  verbose: false
  quiet: false
```

`config.toml`:

```toml
[web-compile]
exit_code = 2
verbose = false
test_run = false
continue_on_error = true
quiet = false

[web-compile.sass]
precision = 5
sourcemap = true
format = "compressed"
encoding = "utf8"

[web-compile.js]
comments = false
encoding = "utf8"

[web-compile.sass.files]
"tests/example_src/example1.scss" = "tests/example_dist/example1.[hash].css"
"tests/example_src/example2.scss" = "tests/example_dist/example2.[hash].css"

[web-compile.js.files]
"tests/example_src/example1.js" = "tests/example_dist/example1.[hash].js"

[web-compile.jinja.files]
"tests/example_src/example1.j2" = "tests/example_dist/example1.txt"
"tests/example_src/example3.j2" = "tests/example_dist/example3.txt"

[web-compile.jinja.variables]
a = "b"
```

`config.json`:

```json
{
  "web-compile": {
    "sass": {
      "files": {
        "tests/example_src/example1.scss": "tests/example_dist/example1.[hash].css",
        "tests/example_src/example2.scss": "tests/example_dist/example2.[hash].css"
      },
      "precision": 5,
      "sourcemap": true,
      "format": "compressed",
      "encoding": "utf8"
    },
    "js": {
      "files": {
        "tests/example_src/example1.js": "tests/example_dist/example1.[hash].js"
      },
      "comments": false,
      "encoding": "utf8"
    },
    "jinja": {
      "files": {
        "tests/example_src/example1.j2": "tests/example_dist/example1.txt",
        "tests/example_src/example3.j2": "tests/example_dist/example3.txt"
      },
      "variables": {
        "a": "b"
      }
    },
    "exit_code": 2,
    "verbose": false,
    "test_run": false,
    "continue_on_error": true,
    "quiet": false
  }
}
```

## Usage

### SCSS Compilation

Simply map a source SCSS file to an output CSS filename.Paths should be relative to the configuration files and `@import` \ `@use`ed partial files will also be read:

```yaml
web-compile:
  sass:
    files:
      src/file.scss: dist/file.css
```

```console
$ web-compile
```

```
src/
    _partial.scss
    file.scss
dist/
    file.css
```

If you use the `sourcemap` option, then a sourcemap will also be output,
and a `sourceMappingURL` comment added to the CSS:

```yaml
web-compile:
  sass:
    files:
      src/file.scss: dist/file.css
    sourcemap: true
```

```console
$ web-compile
```

```
dist/
    file.css
    file.scss.map.json
```

If you add `[hash]` to the CSS filename, then it will be replaced with the content hash.
Also, any existing files, matching the pattern, with a different hash will be removed:

```yaml
web-compile:
  sass:
    files:
      src/file.scss: dist/file.[hash].css
```

```console
$ web-compile
```

```
dist/
    file.beabd761a3703567b4ce06c9a6adde55.css
```

### JavaScript

Javascript files are minified and are configured similarly to SCSS.

```yaml
web-compile:
  js:
    files:
      src/file.js: dist/file.[hash].js
```

```console
$ web-compile
```

```
dist/
    file.beabd761a3703567b4ce06c9a6adde55.js
```

### Jinja Templates

Files can be created from Jinja templates.
These are created after the SCSS and JS files are compiled, and allow for a special `compiled_name` filter,
which converts ab input file path to the compiled file name:

`src/file.j2`:
```jinja
{{ "src/file.scss" | compiled_name }}
{{ var1 }}
```

```yaml
web-compile:
  sass:
    files:
      src/file.scss: dist/file.[hash].css
  jinja:
    files:
      src/file.j2: dist/file.txt
    variables:
      var1: other
```

```console
$ web-compile
```

`dist/file.txt`:
```
file.beabd761a3703567b4ce06c9a6adde55.css
other
```

## Development

To run the tests:

```console
pip install tox
tox -e py37
```

To test out the CLI:

```console
tox -e py37-cli
```

To test the pre-commit hook:

```console
tox -e try-repo
```

For code style:

```console
pip install pre-commit
pre-commit run --all
```

# scss-compile

A CLI for compiling SCSS files to CSS, and associated pre-commit hook.

This CLI is a small wrapper around [libsass-python](https://github.com/sass/libsass-python),
which also aims to be compatible with [pre-commit](https://pre-commit.com/),
and provide a pre-commit hook.

**NOTE**: The package in on alpha release, but looks to be working as intended,
and will be trialled in [sphinx-panels](https://github.com/executablebooks/sphinx-panels),
and then [sphinx-book-theme](https://github.com/executablebooks/sphinx-book-theme).

## Installation

To use directly as a CLI:

```console
pip install scss-compile
scss-compile --help
```

To use *via* pre-commit:

Add to your `.pre-commit-config.yaml`

```yaml
-   repo: https://github.com/executablebooks/scss-compile
    rev: v0.1.0
    hooks:
      - id: scss-compile
        args: [--config=config.yml] # optional
```

## Configuration

You can can configure the compilation directly *via* the CLI or using a configuration file
(simply replace `-` with `_`):

```console
$ scss-compile --help
Usage: scss-compile [OPTIONS] [PATHS]...

  Compile all SCSS files in the paths provided.

  For directories; include all non-partial SCSS files, and for files; if
  partial, include all adjacent, non-partial, SCSS files.

Options:
  --recurse / --no-recurse        For directories, include files in sub-
                                  folders.  [default: True]

  -d, --partial-depth INTEGER     For partial files (starting '_') include all
                                  SCSS files up 'n' parent folders  [default:
                                  0]

  -s, --stop-on-error             Stop on the first compilation error.
  -e, --encoding TEXT             [default: utf8]
  -f, --output-format [nested|expanded|compact|compressed]
                                  [default: compressed]
  -m, --sourcemap                 Output source map.
  -h, --hash-filenames            Add the content hash to filenames:
                                  <filename>#<hash>.css (old hashes will be
                                  removed).

  -t, --translate TEXT            Source to output path translations, e.g.
                                  'src/scss:dist/css' (can be used multiple
                                  times)

  -p, --precision INTEGER         precision for numbers.  [default: 5]
  -q, --quiet                     Remove stdout logging.
  -v, --verbose                   Increase stdout logging.
  --exit-code INTEGER             Exit code when files changed.  [default: 2]
  --no-git                        Do not add new files to a git index.
  --test-run                      Do not delete/create any files.
  --config FILE                   Read default configuration from a file
                                  (allowed extensions: .json, .toml, .yml,
                                  .yaml.)

  --help                          Show this message and exit.
```

`--config` can point to any of three file-formats:

`config.json`:

```json
{
  "scss-compile": {
    "precision": 5,
    "sourcemap": true,
    "hash_filenames": true,
    "output_format": "compressed",
    "partial_depth": 1,
    "translate": ["tests/example_sass:tests/output_css"]
  }
}
```

`config.toml`:

```toml
[scss-compile]
precision = 5
sourcemap = true
hash_filenames = true
output_format = "compressed"
partial_depth = 1
translate = ["tests/example_sass:tests/output_css"]
```

`config.yml`/`config.yaml`:

```yaml
scss-compile:
  precision: 5
  sourcemap: true
  hash_filenames: true
  output_format: compressed
  partial_depth: 1
  translate: ["tests/example_sass:tests/output_css"]
```

## Usage

If you simply specify a normal SCSS file, then the CSS file will be output in the same folder:

```console
$ scss-compile scss/file.scss
```

```
scss/
    file.scss
    file.css
```

If you use the `sourcemap` option, then a sourcemap will also be output,
and a `sourceMappingURL` comment added to the CSS:

```console
$ scss-compile scss/file.scss --sourcemap
```

```
scss/
    file.scss
    file.css
    file.scss.map.json
```

If you use the `hash_filenames` option, then the CSS filename will include the content hash (and any existing file with a different hash will be removed):

```console
$ scss-compile scss/file.scss -- hash-filenames
```

```
scss/
    file.scss
    file#beabd761a3703567b4ce06c9a6adde55.css
```

If you specify a partial file, i.e. ones beginning `_` used *via* `@import` and `@use`,
then all "normal" SCSS files in that folder will be compiled.
If you also use the `partial-depth` option, then files in parent folders will also be compiled.

```console
$ scss-compile scss/imports/_partial.scss -- partial-depth=1
```

```
scss
   /imports
       _partial.scss
    file.scss
    file.css
```

If you set the `--translate` option, then the output files will be "translated" to the specified output path
(which will be created if it does not yet exist):

```console
$ scss-compile scss/file.scss --translate "src/scss:dist/css" --sourcemap
```

```
src/scss/
    file.scss
dist/css/
    file.css
    file.scss.map.json
```

If you specify a directory, then it will first find all SCSS files in that directory,
and recursive sub-folders (unless `--no-recurse` is used), then treat each individual file as above.

## Development

To run the tests:

```console
pip install tox
tox
```

To test out the CLI:

```console
tox -e py37-cli -- --help
```

For code style:

```console
pip install pre-commit
pre-commit run --all
```

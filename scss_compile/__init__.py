__version__ = "0.0.1"

import json
import hashlib
import os
from pathlib import Path
from typing import Set

import click
import click_config_file
import sass
import toml
import yaml


def config_provider(file_path, cmd_name):
    """Read configuration file."""
    _, ext = os.path.splitext(file_path)
    text = Path(file_path).read_text()
    if ext in [".yml", ".yaml"]:
        dct = yaml.safe_load(text)
    elif ext == ".json":
        dct = json.loads(text)
    elif ext == ".toml":
        dct = toml.loads(text)
    else:
        raise IOError("file extension not one of: json, toml, yml, yaml")
    if cmd_name not in dct:
        raise IOError(f"must contain top-level key '{cmd_name}'")
    return dct[cmd_name]


@click.command("scss-compile")
@click.argument(
    "paths", nargs=-1, type=click.Path(exists=True, file_okay=True, dir_okay=True)
)
@click.option(
    "--recurse/--no-recurse",
    default=True,
    is_flag=True,
    show_default=True,
    help="For directories, include files in sub-folders.",
)
@click.option(
    "-d",
    "--partial-depth",
    type=int,
    default=0,
    show_default=True,
    help=(
        "For partial files (starting '_') include all SCSS files up 'n' parent folders"
    ),
)
@click.option(
    "-s", "--stop-on-error", is_flag=True, help="Stop on the first compilation error."
)
@click.option("-e", "--encoding", default="utf8", show_default=True)
@click.option(
    "-f",
    "--output-format",
    type=click.Choice(["nested", "expanded", "compact", "compressed"]),
    default="compressed",
    show_default=True,
)
@click.option("-m", "--sourcemap", is_flag=True, help="Output source map.")
@click.option(
    "-h",
    "--hash-filenames",
    is_flag=True,
    help=(
        "Add the content hash to filenames: "
        "<filename>#<hash>.css (old hashes will be removed)."
    ),
)
@click.option(
    "-t",
    "--translate",
    multiple=True,
    help=(
        "Source to output path translations, e.g. 'src/scss:dist/css' "
        "(can be used multiple times)"
    ),
)
@click.option(
    "-p",
    "--precision",
    default=5,
    type=int,
    show_default=True,
    help="precision for numbers.",
)
@click.option("-q", "--quiet", is_flag=True, help="Remove stdout logging.")
@click.option("-v", "--verbose", is_flag=True, help="Increase stdout logging.")
@click.option("--test-run", is_flag=True, help="Do not delete/create any files.")
@click_config_file.configuration_option(
    provider=config_provider,
    implicit=False,
    help=(
        "Read default configuration from a file "
        "(allowed extensions: .json, .toml, .yml, .yaml.)"
    ),
)
def run_compile(
    paths,
    recurse,
    partial_depth,
    stop_on_error,
    encoding,
    output_format,
    sourcemap,
    hash_filenames,
    translate,
    precision,
    quiet,
    verbose,
    test_run,
):
    """Compile all SCSS files in the paths provided.

    For directories; include all non-partial SCSS files, and
    for files; if partial, include all adjacent, non-partial, SCSS files.
    """
    try:
        translate = (
            {}
            if translate is None
            else {t.split(":", 1)[0]: t.split(":", 1)[1] for t in translate}
        )
    except IndexError:
        raise click.ClickException(f"Malformed translate option: '{translate}'")
    if not quiet:
        config_str = yaml.dump(
            {
                "Compile configuration": {
                    "recurse": recurse,
                    "partial_depth": partial_depth,
                    "output_format": output_format,
                    "hash_filenames": hash_filenames,
                    "translate": translate,
                    "sourcemap": sourcemap,
                    "precision": precision,
                }
            }
        )
        click.echo(config_str.strip())

    if test_run:
        click.secho("Test run only!", fg="yellow")

    # gather all files to be compiled
    all_paths: Set[Path] = set()
    for path_str in paths:
        path = Path(path_str)
        if path.is_dir():
            # look for all scss files in the directory
            for file_path in path.glob(("**/" if recurse else "") + "*.scss"):
                if file_path.is_file():
                    all_paths.add(file_path)
        else:
            all_paths.add(path)

    if verbose:
        click.echo(f"Considered files: {', '.join([str(p) for p in all_paths])}")

    # account for partials and @import/@use in a simple manner
    # TODO we could try to identify @import/@use chains, but that's a lot more complex!
    scss_paths: Set[Path] = set()
    for path in all_paths:
        if not path.name.startswith("_"):
            scss_paths.add(path)
            continue
        parent_dir = path.parent
        for _ in range(partial_depth + 1):
            for file_path in parent_dir.glob("[!_]*.scss"):
                if file_path.is_file():
                    scss_paths.add(file_path)
            parent_dir = parent_dir.parent

    compilation_errors = {}
    for scss_path in scss_paths:

        out_dir = scss_path.parent
        # TODO ensure out_dir relative to root
        for src in sorted(translate, key=lambda key: len(key)):
            if str(out_dir).startswith(src):
                out_dir = Path(translate[src] + str(out_dir)[len(src) :])
                break
        try:
            css_str, sourcemap_str = sass.compile(
                filename=str(scss_path),
                include_paths=[str(scss_path.parent.absolute())],
                output_style=output_format,
                precision=precision,
                source_map_filename=str(scss_path) + ".map.json",
                omit_source_map_url=(not sourcemap),
                source_map_root=os.path.relpath(scss_path.parent, out_dir),
            )
        except sass.CompileError as err:
            compilation_errors[str(scss_path)] = str(err)
            if stop_on_error:
                raise click.ClickException(
                    "Compilations failed:\n"
                    f"{yaml.dump(compilation_errors, default_style='|')}"
                )
            continue

        if not test_run:
            out_dir.mkdir(exist_ok=True, parents=True)

        out_name, _ = os.path.splitext(scss_path.name)
        if hash_filenames:
            # remove old hashes
            for path in out_dir.glob(out_name + "#*.css"):
                if verbose:
                    click.secho(f"Removed: {str(path)}", fg="yellow")
                if not test_run:
                    path.unlink()
            css_out_path = out_dir / (
                out_name
                + "#"
                + hashlib.md5(css_str.encode(encoding)).hexdigest()
                + ".css"
            )
        else:
            css_out_path = out_dir / (out_name + ".css")
        if not test_run:
            css_out_path.write_text(css_str, encoding=encoding)
            if sourcemap:
                (out_dir / (scss_path.name + ".map.json")).write_text(
                    sourcemap_str, encoding=encoding
                )
        if not quiet:
            click.echo(f"Compiled: {str(scss_path)} -> {str(css_out_path)}")

    if compilation_errors:
        raise click.ClickException(
            f"Compilations failed:\n{yaml.dump(compilation_errors, default_style='|')}"
        )

    if not quiet:
        click.secho("Compilation succeeded!", fg="green")

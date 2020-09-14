__version__ = "0.1.3"

import json
import hashlib
import os
from pathlib import Path
import sys
from typing import Optional, Set

import click
import click_config_file
from git import Repo, InvalidGitRepositoryError
import sass
import toml
import yaml


def config_provider(file_path: str, cmd_name: str):
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
        "<filename><hash-prefix><hash>.css (old hashes will be removed)."
    ),
)
@click.option(
    "--hash-prefix",
    default="#",
    show_default=True,
    help="Prefix to use for hashed filenames.",
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
@click.option(
    "--exit-code",
    default=2,
    type=int,
    show_default=True,
    help="Exit code when files changed.",
)
@click.option(
    "--no-git",
    is_flag=True,
    help="Do not add new files to a git index.",
)
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
    exit_code,
    no_git,
    hash_prefix,
    test_run,
):
    """Compile all SCSS files in the paths provided.

    For directories; include all non-partial SCSS files, and
    for files; if partial, include all adjacent, non-partial, SCSS files.
    """

    if no_git:
        git_repo = None
    else:
        try:
            # TODO allow for the cwd to be in a child directory of the repo
            git_repo = Repo(os.getcwd(), search_parent_directories=False)
        except InvalidGitRepositoryError:
            raise click.ClickException(
                f"CWD is not the root of a git repository (use --no-git): {os.getcwd()}"
            )

    try:
        translate = (
            {}
            if translate is None
            else {t.split(":", 1)[0]: t.split(":", 1)[1] for t in translate}
        )
    except IndexError:
        raise click.ClickException(f"Malformed translate option: '{translate}'")
    if verbose:
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
                    "git": git_repo.git_dir if git_repo else None,
                    "exit_code": exit_code,
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
    changed_files = False
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

        # fix to agree with end-of-file-fixer
        css_str = css_str.rstrip() + "\n"
        sourcemap_str = sourcemap_str.rstrip() + "\n"

        if not test_run:
            out_dir.mkdir(exist_ok=True, parents=True)

        out_name, _ = os.path.splitext(scss_path.name)
        if hash_filenames:
            css_out_path = out_dir / (
                out_name
                + hash_prefix
                + hashlib.md5(css_str.encode(encoding)).hexdigest()
                + ".css"
            )
            # remove old hashes
            for path in out_dir.glob(f"{out_name}{hash_prefix}*.css"):
                if path == css_out_path:
                    continue
                if verbose:
                    click.secho(f"Removed: {str(path)}", fg="yellow")
                if not test_run:
                    changed_files = True
                    path.unlink()
        else:
            css_out_path = out_dir / (out_name + ".css")
        if not test_run:

            if update_file(css_out_path, css_str, encoding, git_repo, verbose):
                changed_files = True
            if sourcemap and update_file(
                out_dir / (scss_path.name + ".map.json"),
                sourcemap_str,
                encoding,
                git_repo,
                verbose,
            ):
                changed_files = True

        if not quiet:
            if changed_files:
                click.secho(
                    f"Compiled: {str(scss_path)} -> {str(css_out_path)}", fg="blue"
                )
            elif verbose:
                click.echo(f"Already Exists: {str(scss_path)} -> {str(css_out_path)}")

    if compilation_errors:
        raise click.ClickException(
            f"Compilations failed:\n{yaml.dump(compilation_errors, default_style='|')}"
        )

    if not quiet:
        click.secho("Compilation succeeded!", fg="green")

    if changed_files:
        if not quiet:
            click.secho("File(s) changed", fg="yellow")
        sys.exit(exit_code)


def update_file(
    path: Path, text: str, encoding: str, git_repo: Optional[Repo], verbose: bool
) -> bool:

    if not path.exists():
        path.write_text(text, encoding=encoding)
        if git_repo is not None:
            # this is required, to ensure file creations are picked up by pre-commit
            git_repo.index.add([str(path)], write=True)
            if verbose:
                click.echo(f"Added to git index: {str(path)}")
        return True

    if text != path.read_text(encoding=encoding):
        path.write_text(text, encoding=encoding)
        return True

    return False

__version__ = "0.2.3"

import hashlib
import jinja2
import os
from pathlib import Path
import sys

import click
from git import Repo, InvalidGitRepositoryError
import rjsmin
import sass
import yaml

from .config import config_callback

# configuration file
CONFIG_FILE = click.option(
    "-c",
    "--config",
    "config_path",
    default="web-compile-config.yml",
    type=click.Path(readable=True, dir_okay=False, file_okay=True),
    show_default=True,
    callback=config_callback,
    help="Allowed extensions: json, toml, yml, yaml",
)

# sass options
SASS_FILES = click.option("--sass-files", type=dict, help="File mapping (config only)")
SASS_FORMAT = click.option(
    "--sass-format",
    type=click.Choice(["nested", "expanded", "compact", "compressed"]),
    default="compressed",
    show_default=True,
)
SASS_PRECISION = click.option(
    "--sass-precision",
    default=5,
    type=int,
    show_default=True,
    help="precision for numbers.",
)
SASS_SOURCEMAP = click.option(
    "--sass-sourcemap", is_flag=True, help="Output source map."
)
SASS_ENCODING = click.option("--sass-encoding", default="utf8", show_default=True)

# JS options
JS_FILES = click.option("--js-files", type=dict, help="File mapping (config only)")
JS_COMMENTS = click.option(
    "--js-comments", is_flag=True, help="Keep comments starting with '/*!'."
)
JS_ENCODING = click.option("--js-encoding", default="utf8", show_default=True)

# jinja options
JINJA_FILES = click.option(
    "--jinja-files", type=dict, help="File mapping (config only)"
)
JINJA_ENCODING = click.option("--jinja-encoding", default="utf8", show_default=True)
JINJA_VARIABLES = click.option(
    "--jinja-variables", type=dict, help="Global variable mapping (config only)"
)

# general options
QUIET = click.option("-q", "--quiet", is_flag=True, help="Remove stdout logging.")
VERBOSE = click.option("-v", "--verbose", is_flag=True, help="Increase stdout logging.")
GIT_ADD = click.option(
    "--git-add/--no-git-add",
    is_flag=True,
    default=True,
    show_default=True,
    help="Add new files to git index.",
)
TEST_RUN = click.option(
    "--test-run", is_flag=True, help="Do not delete/create any files."
)
CONTINUE_ON_ERROR = click.option(
    "--continue-on-error", is_flag=True, help="Do not stop on the first error."
)
EXIT_CODE = click.option(
    "--exit-code",
    default=3,
    type=int,
    show_default=True,
    help="Exit code when files changed.",
)


@click.command("web-compile")
@click.version_option(__version__)
# @click.argument("files", nargs=-1, type=click.Path(file_okay=True, dir_okay=False))
@CONFIG_FILE
@SASS_FILES
@SASS_FORMAT
@SASS_PRECISION
@SASS_SOURCEMAP
@SASS_ENCODING
@JS_FILES
@JS_COMMENTS
@JS_ENCODING
@JINJA_FILES
@JINJA_VARIABLES
@JINJA_ENCODING
@GIT_ADD
@CONTINUE_ON_ERROR
@EXIT_CODE
@TEST_RUN
@QUIET
@VERBOSE
def run_compile(
    config_path: Path,
    sass_files: dict,
    sass_format: str,
    sass_precision: int,
    sass_sourcemap: bool,
    sass_encoding: str,
    js_files: dict,
    js_comments: bool,
    js_encoding: str,
    jinja_files: dict,
    jinja_variables: dict,
    jinja_encoding: str,
    quiet: bool,
    verbose: bool,
    exit_code: int,
    git_add: bool,
    test_run: bool,
    continue_on_error: bool,
):
    """Compile web assets."""
    root = config_path.parent.absolute()

    if verbose:
        click.secho("Compile configuration", fg="blue")
        config_str = yaml.dump(
            {
                "config": str(config_path.absolute()),
                "sass": {
                    "format": sass_format,
                    "precision": sass_precision,
                    "sourcemap": sass_sourcemap,
                    "encoding": sass_encoding,
                },
                "js": {
                    "comments": js_comments,
                    "encoding": js_encoding,
                },
                "jinja": {"encoding": jinja_encoding, "variables": jinja_variables},
                "git_add": git_add,
                "exit_code": exit_code,
                "test_run": test_run,
                "continue_on_error": continue_on_error,
            }
        )
        click.echo(config_str.strip())

    if git_add:
        try:
            git_repo = Repo(root, search_parent_directories=False)
        except InvalidGitRepositoryError:
            raise click.ClickException(
                "Config file not the root of a git repository (use --no-add-git)"
            )
    else:
        git_repo = None

    changed_files = False
    compilation_errors = {}
    file_map = {}

    changed_sass = compile_sass(
        sass_files or {},
        root,
        sass_format,
        sass_precision,
        sass_sourcemap,
        sass_encoding,
        git_repo,
        verbose,
        quiet,
        test_run,
        continue_on_error,
        compilation_errors,
        file_map,
    )
    if changed_sass:
        changed_files = True

    changed_js = minify_js(
        js_files or {},
        root,
        js_comments,
        js_encoding,
        git_repo,
        verbose,
        quiet,
        test_run,
        continue_on_error,
        compilation_errors,
        file_map,
    )
    if changed_js:
        changed_files = True

    changed_jinja = compile_jinja(
        jinja_files,
        root,
        jinja_encoding,
        jinja_variables,
        git_repo,
        verbose,
        quiet,
        test_run,
        continue_on_error,
        compilation_errors,
        file_map,
    )
    if changed_jinja:
        changed_files = True

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


def compile_sass(
    sass_files,
    root,
    sass_format,
    sass_precision,
    sass_sourcemap,
    sass_encoding,
    git_repo,
    verbose,
    quiet,
    test_run,
    continue_on_error,
    compilation_errors,
    file_map,
):
    """sass compilation."""
    changed_files = False

    for sass_input_str, sass_output_str in sass_files.items():
        sass_input = root / sass_input_str
        sass_output = root / sass_output_str
        if not sass_input.exists():
            if continue_on_error:
                continue
            compilation_errors[str(sass_input)] = "Path does not exist"
            raise click.ClickException(
                "SASS compilation failed:\n"
                f"{yaml.dump(compilation_errors, default_style='|')}"
            )
        try:
            css_str, sourcemap_str = sass.compile(
                filename=str(sass_input),
                include_paths=[str(sass_input.parent.absolute())],
                output_style=sass_format,
                precision=sass_precision,
                source_map_filename=str(sass_input) + ".map.json",
                omit_source_map_url=(not sass_sourcemap),
                source_map_root=os.path.relpath(sass_input.parent, sass_output.parent),
            )
        except sass.CompileError as err:
            compilation_errors[str(sass_input)] = str(err)
            if continue_on_error:
                continue
            raise click.ClickException(
                "SASS compilation failed:\n"
                f"{yaml.dump(compilation_errors, default_style='|')}"
            )

        if "[hash]" in sass_output.name:
            file_hash = hash_file(css_str, sass_encoding)
            new_sass_output = sass_output.parent / sass_output.name.replace(
                "[hash]", file_hash
            )
            for old_output in sass_output.parent.glob(
                sass_output.name.replace("[hash]", "*")
            ):
                if old_output.absolute() == new_sass_output.absolute():
                    continue
                if verbose:
                    click.secho(f"Removed: {str(old_output)}", fg="yellow")
                if not test_run:
                    changed_files = True
                    old_output.unlink()
            sass_output = new_sass_output

        file_map[sass_input.relative_to(root)] = sass_output.relative_to(root)

        if update_file(
            sass_output,
            css_str,
            sass_encoding,
            verbose,
            quiet,
            test_run,
            sass_input,
            git_repo,
        ):
            changed_files = True

        if sass_sourcemap and update_file(
            sass_output.parent / (sass_input.name + ".map.json"),
            sourcemap_str,
            sass_encoding,
            verbose,
            quiet,
            test_run,
            sass_input,
            git_repo,
        ):
            changed_files = True

    return changed_files


def minify_js(
    js_files,
    root,
    js_comments,
    js_encoding,
    git_repo,
    verbose,
    quiet,
    test_run,
    continue_on_error,
    compilation_errors,
    file_map,
):
    """sass compilation."""
    changed_files = False

    for input_str, output_str in js_files.items():
        input_path = root / input_str
        output_path = root / output_str
        if not input_path.exists():
            compilation_errors[str(input_path)] = "Path does not exist"
            if continue_on_error:
                continue
            raise click.ClickException(
                "JS compilation failed:\n"
                f"{yaml.dump(compilation_errors, default_style='|')}"
            )
        try:
            js_str = rjsmin.jsmin(input_path.read_text(), js_comments)
            # ensure compatibility with end-of-file-fixer
            js_str = js_str.rstrip() + os.linesep
        except Exception as err:
            compilation_errors[str(input_path)] = str(err)
            if continue_on_error:
                continue
            raise click.ClickException(
                "SASS compilation failed:\n"
                f"{yaml.dump(compilation_errors, default_style='|')}"
            )

        if "[hash]" in output_path.name:
            file_hash = hash_file(js_str, js_encoding)
            new_output_path = output_path.parent / output_path.name.replace(
                "[hash]", file_hash
            )
            for old_output in output_path.parent.glob(
                output_path.name.replace("[hash]", "*")
            ):
                if old_output.absolute() == new_output_path.absolute():
                    continue
                if verbose:
                    click.secho(f"Removed: {str(old_output)}", fg="yellow")
                if not test_run:
                    changed_files = True
                    old_output.unlink()
            output_path = new_output_path

        file_map[input_path.relative_to(root)] = output_path.relative_to(root)

        if update_file(
            output_path,
            js_str,
            js_encoding,
            verbose,
            quiet,
            test_run,
            input_path,
            git_repo,
        ):
            changed_files = True

    return changed_files


def compile_jinja(
    jinja_files,
    root,
    jinja_encoding,
    jinja_variables,
    git_repo,
    verbose,
    quiet,
    test_run,
    continue_on_error,
    compilation_errors,
    file_map,
):
    changed_files = False

    jinja_env = jinja2.Environment()
    jinja_env.globals.update(jinja_variables or {})

    def _get_compiled_name(path):
        if not path or Path(path) not in file_map:
            raise KeyError(f"No compiled path: {path}")
        return file_map.get(Path(path)).name

    def _get_hash(path):
        if not path or Path(path) not in file_map:
            raise KeyError(f"No compiled path: {path}")
        input_path = root / Path(path)
        return hash_file(input_path.read_text("utf8"))

    jinja_env.filters["compiled_name"] = _get_compiled_name
    jinja_env.filters["hash"] = _get_hash
    for input_str, output_str in (jinja_files or {}).items():
        input_path = root / input_str
        output_path = root / output_str
        if not input_path.exists():
            compilation_errors[str(input_path)] = "Path does not exist"
            if continue_on_error:
                continue
            raise click.ClickException(
                "Jinja compilation failed:\n"
                f"{yaml.dump(compilation_errors, default_style='|')}"
            )
        try:
            jinja_str = jinja_env.from_string(
                input_path.read_text(jinja_encoding)
            ).render()
            # ensure compatibility with end-of-file-fixer
            jinja_str = jinja_str.rstrip() + os.linesep
        except Exception as err:
            compilation_errors[str(input_path)] = str(err)
            if continue_on_error:
                continue
            raise click.ClickException(
                "Jinja compilation failed:\n"
                f"{yaml.dump(compilation_errors, default_style='|')}"
            )

        if update_file(
            output_path,
            jinja_str,
            jinja_encoding,
            verbose,
            quiet,
            test_run,
            input_path,
            git_repo,
        ):
            changed_files = True

    return changed_files


def update_file(
    path: Path,
    text: str,
    encoding: str,
    verbose: bool,
    quiet: bool,
    test_run: bool,
    in_path: Path,
    git_repo,
) -> bool:
    """Update a file."""
    changed = False

    if not path.exists():
        if not test_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding=encoding)
            if git_repo is not None:
                # this is required, to ensure file creations are picked up by pre-commit
                git_repo.index.add([str(path)], write=True)
                if verbose:
                    click.echo(f"Added to git index: {str(path)}")
        changed = True

    elif text != path.read_text(encoding=encoding):
        if not test_run:
            path.write_text(text, encoding=encoding)
        changed = True

    if changed and not quiet:
        click.secho(f"Compiled: {str(in_path)} -> {str(path)}", fg="blue")
    if not changed and verbose:
        click.echo(f"Already Exists: {str(in_path)} -> {str(path)}")

    return changed


def hash_file(string: str, encoding: str = "utf8"):
    return hashlib.md5(string.encode(encoding)).hexdigest()

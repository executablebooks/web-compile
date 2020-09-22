import os
from pathlib import Path
import shutil

from click.testing import CliRunner
from git import Repo
import pytest
import yaml

from web_compile import run_compile


@pytest.fixture()
def src_folder(tmp_path: Path) -> Path:
    """Copy the scss folder to a temporary folder, and initialise it as git repo."""
    src = tmp_path / "src"
    shutil.copytree(Path(__file__).parent / "example_src", src)
    repo = Repo.init(str(tmp_path))
    repo.index.commit("initial commit")
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)
    shutil.rmtree(tmp_path)


def create_config(src_folder, data=None):
    config = src_folder / "config.yml"
    config.write_text(yaml.dump({"web-compile": data or {}}), encoding="utf8")
    return config


def test_help():
    result = CliRunner().invoke(run_compile, ["--help"])
    assert result.exit_code == 0, result.output


def test_empty_config(src_folder: Path):
    config = src_folder / "config.yml"
    config.touch()
    result = CliRunner().invoke(run_compile, ["-c", str(config)])
    assert result.exit_code != 0, result.output
    assert "File is empty" in result.output


def test_no_files(src_folder: Path):
    config = create_config(src_folder)
    result = CliRunner().invoke(run_compile, ["-c", str(config)])
    assert result.exit_code == 0, result.output


def test_sass_basic(src_folder: Path):
    config = create_config(
        src_folder, {"sass_files": {"src/example1.scss": "dist/example1.css"}}
    )
    result = CliRunner().invoke(run_compile, ["-c", str(config)])
    assert result.exit_code == 3, result.output
    assert (src_folder / "dist" / "example1.css").exists(), result.output
    assert len(list((src_folder / "dist").glob("*"))) == 1

    # re-run
    result = CliRunner().invoke(run_compile, ["-c", str(config)])
    assert result.exit_code == 0, result.output


def test_sass_sourcemap(src_folder: Path):
    config = create_config(
        src_folder,
        {
            "sass": {
                "files": {"src/example1.scss": "dist/example1.css"},
                "sourcemap": True,
            }
        },
    )
    result = CliRunner().invoke(run_compile, ["-c", str(config)])
    assert result.exit_code == 3, result.output
    assert (src_folder / "dist" / "example1.css").exists(), result.output
    assert (src_folder / "dist" / "example1.scss.map.json").exists(), result.output


def test_sass_hash(src_folder: Path):
    config = create_config(
        src_folder, {"sass_files": {"src/example1.scss": "dist/example1.[hash].css"}}
    )
    result = CliRunner().invoke(run_compile, ["-c", str(config)])
    assert result.exit_code == 3, result.output

    assert (
        src_folder / "dist" / "example1.ba380fe0e8b24cb752044f2edcd66d87.css"
    ).exists(), result.output


def test_js_basic(src_folder: Path):
    config = create_config(
        src_folder, {"js_files": {"src/example1.js": "dist/example1.js"}}
    )
    result = CliRunner().invoke(run_compile, ["-c", str(config)])
    assert result.exit_code == 3, result.output
    assert (src_folder / "dist" / "example1.js").exists(), result.output


def test_js_hash(src_folder: Path):
    config = create_config(
        src_folder, {"js_files": {"src/example1.js": "dist/example1.[hash].js"}}
    )
    result = CliRunner().invoke(run_compile, ["-c", str(config)])
    assert result.exit_code == 3, result.output

    assert (
        src_folder / "dist" / "example1.36fb66cd32ac08ace70a7132f8173a9b.js"
    ).exists(), result.output


def test_jinja_basic(src_folder: Path):
    config = create_config(
        src_folder,
        {
            "jinja": {
                "files": {"src/example1.j2": "dist/example1.txt"},
                "variables": {"a": "b"},
            }
        },
    )
    result = CliRunner().invoke(run_compile, ["-c", str(config)])
    assert result.exit_code == 3, result.output
    assert (src_folder / "dist" / "example1.txt").exists(), result.output
    assert "b" in (src_folder / "dist" / "example1.txt").read_text("utf8")


def test_full(src_folder: Path):
    config = create_config(
        src_folder,
        {
            "sass": {
                "files": {
                    "src/example1.scss": "dist/example1.[hash].css",
                    "src/example2.scss": "dist/example2.[hash].css",
                },
                "precision": 5,
                "sourcemap": True,
                "format": "compressed",
                "encoding": "utf8",
            },
            "js": {
                "files": {"src/example1.js": "dist/example1.[hash].js"},
                "comments": False,
                "encoding": "utf8",
            },
            "jinja": {
                "files": {
                    "src/example1.j2": "dist/example1.txt",
                    "src/example2.j2": "dist/example2.txt",
                },
                "variables": {"a": "b"},
            },
            "exit_code": 4,
            "verbose": True,
            "test_run": False,
            "continue_on_error": True,
            "quiet": False,
        },
    )
    result = CliRunner().invoke(run_compile, ["-c", str(config)])
    assert result.exit_code == 4, result.output
    assert (src_folder / "dist" / "example2.txt").exists(), result.output
    text = (src_folder / "dist" / "example2.txt").read_text("utf8")
    # print(text)
    assert "example1.120bc14042c23711b51a07133e9dcabd.css" in text, text
    assert "example1.36fb66cd32ac08ace70a7132f8173a9b.js" in text, text
    assert len(list((src_folder / "dist").glob("*"))) == 7

    # re-run
    result = CliRunner().invoke(run_compile, ["-c", str(config)])
    assert result.exit_code == 0, result.output
    assert len(list((src_folder / "dist").glob("*"))) == 7

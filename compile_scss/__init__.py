__version__ = "0.0.1"

import hashlib
import os
from pathlib import Path
from subprocess import check_output
import sys

CONFIG_FILE = ".scss-compile.yml"

def run_compile():
    import sass
    import yaml

    # TODO for simplicity we'll start by assuming the CWD is root
    # I think pre-commit always changes this to the root anyway
    root_dir = Path(os.getcwd())
    # paths passed from pre-commit
    paths = [Path(path) for path in sys.argv[1:]]

    if not (root_dir / CONFIG_FILE).exists():
        raise IOError(f"The config file does not exist: {CONFIG_FILE}")

    config = yaml.safe_load((root_dir / CONFIG_FILE).read_text(encoding="utf8"))
    source_dir = config.get("SOURCES_PATH", None)
    target_dir = config.get("TARGET_PATH", None)

    assert source_dir is not None, f"config does not contain SOURCES_PATH"
    assert target_dir is not None, f"config does not contain SOURCES_PATH"

    assert Path(source_dir).is_dir(), f"SOURCES_PATH is not a directory"
    assert Path(target_dir).is_dir(), f"TARGET_PATH is not a directory"

    # get initial hash of only committed/staged files and content
    initial_paths = check_output(["git", "ls-files", "--cached", target_dir]).decode("utf8").splitlines()
    initial_hashed = {}
    for initial_path in sorted(initial_paths):
        hashed = hashlib.md5(check_output(["git", "show", "--format=raw", f":{initial_path}"]))
        initial_hashed[initial_path] = hashed.hexdigest()
    # initial_hashed = check_output(["git", "hash-object"] + list(sorted(initial_paths)))

    sass.compile(dirname=(source_dir, target_dir))

    # get final hash of working dir files and content
    final_hashed = {}
    for path in Path(target_dir).glob("**/*"):
        if path.is_file():
            final_hashed[str(path)] = hashlib.md5(path.read_bytes()).hexdigest()

    if initial_hashed != final_hashed:
        raise SystemExit(f"Hashes changed:\nInitial: {initial_hashed}\nFinal: {final_hashed}")

import json
from pathlib import Path

import click
import toml
import yaml

TOP_LEVEL = "web-compile"


def read_config(path: Path, encoding="utf8"):
    text = path.read_text(encoding)
    if not text:
        raise IOError("File is empty")
    if path.name.endswith(".yml") or path.name.endswith(".yaml"):
        config = yaml.safe_load(text)
    elif path.name.endswith(".json"):
        config = json.loads(text)
    elif path.name.endswith(".toml"):
        config = toml.loads(text)
    else:
        raise IOError("file extension not one of: json, toml, yml, yaml")
    if TOP_LEVEL not in config:
        raise IOError(f"must contain top-level key '{TOP_LEVEL}'")
    config = config[TOP_LEVEL] or {}

    # combine top level
    for top_key in ["js", "sass", "jinja"]:
        top_config = config.pop(top_key, {})
        for key, value in top_config.items():
            config[f"{top_key}_{key}"] = value

    return config


def config_callback(ctx: click.Context, param: click.Option, path: str):
    path = Path(path)
    if not path.exists():
        raise click.BadOptionUsage(
            param.name, f"Configuration file does not exist: {path}", ctx
        )
    try:
        config = read_config(path)
    except Exception as e:
        raise click.BadOptionUsage(
            param.name, "Error reading configuration file: {}".format(e), ctx
        )
    ctx.default_map = ctx.default_map or {}
    ctx.default_map.update(config)

    return path

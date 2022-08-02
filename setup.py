#!/usr/bin/env python
from pathlib import Path
from setuptools import setup, find_packages

version = [
    line
    for line in Path("web_compile/__init__.py").read_text().split("\n")
    if "__version__" in line
]
version = version[0].split(" = ")[-1].strip('"')
readme_text = Path("./README.md").read_text()

setup(
    name="web-compile",
    version=version,
    description=("A CLI to compile/minify SCSS & JS, and associated pre-commit hook."),
    long_description=readme_text,
    long_description_content_type="text/markdown",
    author="Chris Sewell",
    author_email="chrisj_sewell@hotmail.com",
    url="https://github.com/executablebooks/web-compile",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[
        "click>=7.1.2,<10.0.0",
        "jinja2~=3.0.3",
        "libsass~=0.20.1",
        "gitpython~=3.1.8",
        "pyyaml",
        "rjsmin~=1.1.0",
        "toml",
    ],
    extras_require={
        "testing": ["pytest~=6.0.1"],
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    keywords="sass scss js jinja compile pre-commit",
    entry_points={
        "console_scripts": [
            "web-compile=web_compile:run_compile",
        ],
    },
)

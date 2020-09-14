#!/usr/bin/env python
from pathlib import Path
from setuptools import setup, find_packages

version = [
    line
    for line in Path("scss_compile/__init__.py").read_text().split("\n")
    if "__version__" in line
]
version = version[0].split(" = ")[-1].strip('"')
readme_text = Path("./README.md").read_text()

setup(
    name="scss-compile",
    version=version,
    description=(
        "A CLI for compiling SCSS files to CSS, and associated pre-commit hook."
    ),
    long_description=readme_text,
    long_description_content_type="text/markdown",
    author="Chris Sewell",
    author_email="chrisj_sewell@hotmail.com",
    url="https://github.com/executablebooks/scss-compile",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[
        "click~=7.1.2",
        "click-config-file~=0.6.0",
        "libsass~=0.20.1",
        "gitpython~=3.1.8",
        "pyyaml",
        "toml",
    ],
    extras_require={
        "testing": ["pytest~=6.0.1"],
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    keywords="sass scss compile pre-commit",
    entry_points={
        "console_scripts": [
            "scss-compile=scss_compile:run_compile",
        ],
    },
)

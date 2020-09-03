#!/usr/bin/env python
from pathlib import Path
from setuptools import setup, find_packages

version = [
    line
    for line in Path("compile_scss/__init__.py").read_text().split("\n")
    if "__version__" in line
]
version = version[0].split(" = ")[-1].strip('"')
readme_text = Path("./README.md").read_text()

setup(
    name="pre-commit-scss",
    version="version",
    description="A pre-commit hook for compiling SCSS files to CSS.",
    long_description=readme_text,
    long_description_content_type="text/markdown",
    author="Chris Sewell",
    author_email="chrisj_sewell@hotmail.com",
    url="https://github.com/executablebooks/pre-commit-scss",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["libsass~=0.20.1", "pyyaml"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    keywords="pre-commit sass scss",
    entry_points={
        "console_scripts": [
            "compile-scss=compile_scss:run_compile",
        ],
    },
)

#!/usr/bin/env python3
"""
Setup script for the Docker-based sandbox SDK.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="localsandbox",
    version="0.1.0",
    description="Docker-based sandbox SDK for code execution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="LocalSandbox Team",
    author_email="team@localsandbox.dev",
    url="https://github.com/localsandbox/localsandbox",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        # No external dependencies - uses only standard library
        # Docker is required but installed separately
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Emulators",
    ],
    keywords="sandbox docker container code-execution",
    project_urls={
        "Bug Reports": "https://github.com/localsandbox/localsandbox/issues",
        "Source": "https://github.com/localsandbox/localsandbox",
    },
)
#!/usr/bin/env python3
"""
Setup script for LocalSandbox MCP Server

This setup script allows the entire project to be installed as a Python package
with all dependencies and command-line tools.
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "LocalSandbox MCP Server - A Model Context Protocol server for code execution in sandboxed environments"

# Read requirements from mcp-server/requirements.txt
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'mcp-server', 'requirements.txt')
    requirements = []
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    # Remove inline comments
                    if '#' in line:
                        line = line.split('#')[0].strip()
                    # Skip development dependencies
                    if not any(dev_dep in line.lower() for dev_dep in ['pytest', 'black', 'flake8', 'mypy']):
                        requirements.append(line)
    return requirements

setup(
    name="localsandbox-mcp-server",
    version="1.0.0",
    description="LocalSandbox MCP Server - A Model Context Protocol server for code execution",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Eric Zane",
    author_email="radiumce@gmail.com",
    url="https://github.com/radiumce/localsandbox",
    
    # Package configuration - include both mcp-server and python packages
    packages=[
        'mcp_server',
        'wrapper', 
        'sandbox'
    ],
    package_dir={
        'mcp_server': 'mcp-server/mcp_server',
        'wrapper': 'mcp-server/wrapper',
        'sandbox': 'python/sandbox',
    },
    include_package_data=True,
    python_requires=">=3.8",
    
    # Dependencies
    install_requires=read_requirements(),
    
    # Entry points for command-line usage
    entry_points={
        'console_scripts': [
            'localsandbox-mcp-server=mcp_server.main:main',
            'mcp-server=mcp_server.main:main',
            'start-localsandbox=mcp_server.scripts:start_docker_server',
        ],
    },
    
    # Package metadata
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
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: System :: Distributed Computing",
        "Topic :: Software Development :: Code Generators",
        "Topic :: System :: Emulators",
    ],
    
    # Keywords for PyPI
    keywords="mcp model-context-protocol localsandbox sandbox http-server code-execution docker AI Agent",
    

    
    # Additional package data
    package_data={
        'mcp_server': [
            '*.md',
            '*.txt',
            '*.yml',
            '*.yaml',
            '*.sh',
            '.env.*',
        ],
        'wrapper': [
            '*.md',
            '*.txt',
            '*.yml',
            '*.yaml',
        ],
    },
    
    # Extras for optional dependencies
    extras_require={
        'dev': [
            'black>=22.0.0',
            'flake8>=5.0.0',
            'mypy>=1.0.0',
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'pytest-mock>=3.10.0',
        ],
        'test': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'pytest-mock>=3.10.0',
        ],
    },
    
    # Zip safety
    zip_safe=False,
)
#!/usr/bin/env python3
"""
Setup script for PyLedger - A Python-based double-entry accounting system.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="pyledger",
    version="1.0.0",
    author="Dick Chan",
    author_email="dickchan@example.com",
    description="A Python-based double-entry accounting system with invoice and purchase order management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dickhfchan/pyledger",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Office/Business :: Financial :: Accounting",
    ],
    python_requires=">=3.12",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "pyledger=pyledger.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 
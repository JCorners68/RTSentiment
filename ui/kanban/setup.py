#!/usr/bin/env python
"""
Kanban CLI Setup
"""
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="kanban-cli",
    version="0.1.0",
    description="CLI Kanban board with agentic pipeline integration",
    author="Real Sentiment Team",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    entry_points="""
        [console_scripts]
        kanban=src.main:cli
    """,
    python_requires=">=3.8",
)

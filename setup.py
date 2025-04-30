from setuptools import setup, find_packages

setup(
    name="iceberg_lake",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "tabulate",
        "jaydebeapi",
        "jpype1",
        "pyiceberg>=0.9.0",
        "fastapi",
        "uvicorn"
    ]
)
import sys
from setuptools import setup
from setuptools import find_packages

PY3 = sys.version_info >= (3,0)

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='oapi3',
    version='0.3.7',
    author="Mayorov Evgeny",
    author_email="motormen@gmail.com",
    description="Validator of openapi3 requests and responses",
    packages=find_packages(),
    package_dir={'oapi3': 'oapi3'},
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SmartTeleMax/oapi3",
    install_requires=[
        'pyyaml',
        'jsonschema',
        'openapi_spec_validator',
    ],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)

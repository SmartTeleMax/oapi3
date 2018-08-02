import sys
from setuptools import setup
from setuptools import find_packages

PY3 = sys.version_info >= (3,0)

setup(
    name='oapi3',
    version='0.1',
    packages=find_packages(),
    package_dir={'oapi3': 'oapi3'},
    install_requires=[
        'pyyaml',
        'jsonschema==2.6',
        'openapi_spec_validator',
    ],
)

import pytest

from oapi3 import open_schema

@pytest.fixture
def schema():
    return open_schema('tests/yaml/api.yaml') 

"""
Openapi3 schema library

1. Open and resolve openapi3 schema

    import openapi3
    schema = openapi3.open_schema('api.yaml')


2. Validate requests and responses

    schema.validate_request(path, operation, query, media_type, body)
    schema.validate_response(path, operation, status_code, media_type, body)

3. Create client to remote api

    client = Client('http://server/api', schema)
    client.some_method(
        params={'item_id': 10},
        body={'some_key': 'some_date'},
    )
"""
from . import exceptions
from .client import Client
# flake8: noqa: F401
from .resolve import open_schema

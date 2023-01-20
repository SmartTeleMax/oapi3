import pytest
import json
from oapi3 import exceptions


def test_response_code(schema):
    schema.validate_response(
        '/test_response_code',
        'get',
        200,
        'application/json',
        {},
    )
    with pytest.raises(exceptions.ResponseCodeNotAllowed):
        schema.validate_response(
            '/test_response_code',
            'get',
            400,
            'application/json',
            {},
        )

    schema.validate_response(
        '/test_response_code_with_default',
        'get',
        200,
        'application/json',
        {},
    )
    schema.validate_response(
        '/test_response_code_with_default',
        'get',
        400,
        'application/json',
        {},
    )

def test_response_media_type(schema):
    # application/json
    schema.validate_response(
        '/test_response_media_type',
        'get',
        200,
        'application/json',
        {},
    )

    with pytest.raises(exceptions.MediaTypeNotAllowed):
        schema.validate_response(
            '/test_response_media_type',
            'get',
            200,
            'text/plain',
            {},
        )
    # text/*
    schema.validate_response(
        '/test_response_media_type',
        'get',
        400,
        'text/plain',
        {},
    )
    schema.validate_response(
        '/test_response_media_type',
        'get',
        400,
        'text/html',
        {},
    )
    with pytest.raises(exceptions.MediaTypeNotAllowed):
        schema.validate_response(
            '/test_response_media_type',
            'get',
            400,
            'application/json',
            {},
        )

    schema.validate_response(
        '/test_response_media_type',
        'get',
        500,
        'text/plain',
        {},
    )
    schema.validate_response(
        '/test_response_media_type',
        'get',
        500,
        'application/json',
        {},
    )


def test_response_body(schema):
    schema.validate_response(
        '/test_response_body',
        'get',
        200,
        'application/json',
        {'aaa': 1},
    )

    with pytest.raises(exceptions.BodyValidationError):
        schema.validate_response(
            '/test_response_body',
            'get',
            200,
            'application/json',
            {},
        )
        schema.validate_response(
            '/test_response_body',
            'get',
            200,
            'application/json',
            {'aaa': 'ssss'},
        )
        schema.validate_response(
            '/test_response_body',
            'get',
            200,
            'application/json',
            None,
        )

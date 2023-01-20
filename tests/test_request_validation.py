import pytest
import json
from oapi3 import exceptions


def test_request_path(schema):
    schema.validate_request(
        '/test_request_path',
        'get',
        {},
        'application/json',
        None,
    )
    with pytest.raises(exceptions.PathNotFound):
        schema.validate_request(
            '/test_request_path/',
            'get',
            {},
            'application/json',
            None,
        )

    with pytest.raises(exceptions.PathNotFound):
        schema.validate_request(
            '/test_request_path_not_found',
            'get',
            {},
            'application/json',
            None,
        )


def test_request_path_params(schema):
    result = schema.validate_request(
        '/test_request_path_params/aaa/4',
        'get',
        {},
        'application/json',
        None,
    )
    assert set(result['path_params']) == {'param1', 'param2'}
    assert result['path_params']['param1'] == 'aaa'
    assert result['path_params']['param2'] == 4

    with pytest.raises(exceptions.PathParamValidationError):
        schema.validate_request(
            '/test_request_path_params/aaa/fff',
            'get',
            {},
            'application/json',
            None,
        )


def test_request_operations(schema):
    result = schema.validate_request(
        '/test_request_operations',
        'get',
        {},
        'application/json',
        None,
    )
    assert result['operation'] == 'get'
    assert result['operation_id'] == 'test_request_operations_get'

    result = schema.validate_request(
        '/test_request_operations',
        'put',
        {},
        'application/json',
        None,
    )
    assert result['operation'] == 'put'
    assert result['operation_id'] == 'test_request_operations_put'

    with pytest.raises(exceptions.OperationNotAllowed):
        schema.validate_request(
            '/test_request_operations',
            'post',
            {},
            'application/json',
            None,
        )

def test_request_query_params(schema):
    with pytest.raises(exceptions.QueryParamValidationError):
        result = schema.validate_request(
            '/test_request_query_params',
            'get',
            {'param': 'xxx'},
            'application/json',
            None,
        )
    result = schema.validate_request(
        '/test_request_query_params',
        'get',
        {'param_required': 'yyy'},
        'application/json',
        None,
    )
    assert set(result['query']) == {'param_required'}
    assert result['query']['param_required'] == 'yyy'
    result = schema.validate_request(
        '/test_request_query_params',
        'get',
        {'param': 'xxx', 'param_required': 'yyy'},
        'application/json',
        None,
    )
    assert set(result['query']) == {'param', 'param_required'}
    assert result['query']['param'] == 'xxx'
    assert result['query']['param_required'] == 'yyy'
    result = schema.validate_request(
        '/test_request_query_params',
        'get',
        {'param': 'xxx', 'param_required': 'yyy', 'param_int': '44'},
        'application/json',
        None,
    )
    assert set(result['query']) == {'param', 'param_required', 'param_int'}
    assert result['query']['param'] == 'xxx'
    assert result['query']['param_required'] == 'yyy'
    assert result['query']['param_int'] == 44

    with pytest.raises(exceptions.QueryParamValidationError):
        result = schema.validate_request(
            '/test_request_query_params',
            'get',
            {'param': 'xxx', 'param_required': 'yyy', 'param_int': 'ddd'},
            'application/json',
            None,
        )


def test_request_json_query_params(schema):
    result = schema.validate_request(
        '/test_request_json_query_params',
        'get',
        {'param_json': json.dumps({'test': 4})},
        'application/json',
        None,
    )
    assert result['query']['param_json'] == {'test': 4}

    with pytest.raises(exceptions.QueryParamValidationError):
        schema.validate_request(
            '/test_request_json_query_params',
            'get',
            {'param_json': 'xxx'},
            'application/json',
            None,
        )
        schema.validate_request(
            '/test_request_json_query_params',
            'get',
            {'param_json': json.dumps({'test': 'xxx'})},
            'application/json',
            None,
        )
        schema.validate_request(
            '/test_request_json_query_params',
            'get',
            {'param_json': json.dumps({'test1': 'xxx'})},
            'application/json',
            None,
        )
        schema.validate_request(
            '/test_request_array_query_params',
            'get',
            {'param_array_not_exists': '1'},
            'application/json',
            None,
        )


def test_request_array_query_params(schema):
    result = schema.validate_request(
        '/test_request_array_query_params',
        'get',
        {'param_array_form_false': 'aaa,bbb,ccc'},
        'application/json',
        None,
    )
    assert result['query']['param_array_form_false'] == ['aaa', 'bbb', 'ccc']

    result = schema.validate_request(
        '/test_request_array_query_params',
        'get',
        {'param_array_pipe_false': '1|2|4'},
        'application/json',
        None,
    )
    assert result['query']['param_array_pipe_false'] == [1, 2, 4]

    with pytest.raises(exceptions.QueryParamValidationError):
        schema.validate_request(
            '/test_request_array_query_params',
            'get',
            {'param_array_pipe_false': '1|aaa|4'},
            'application/json',
            None,
        )

    result = schema.validate_request(
        '/test_request_array_query_params',
        'get',
        {'param_array_space_false': '1 2 4'},
        'application/json',
        None,
    )
    assert result['query']['param_array_space_false'] == [1, 2, 4]

    with pytest.raises(exceptions.QueryParamValidationError):
        schema.validate_request(
            '/test_request_array_query_params',
            'get',
            {'param_array_space_false': '1 aaa 4'},
            'application/json',
            None,
        )


def test_request_body(schema):
    result = schema.validate_request(
        '/test_request_body',
        'post',
        {},
        'application/json',
        {'aaa': 1},
    )
    assert result['body_dict'] == {'aaa': 1}

    result = schema.validate_request(
        '/test_request_body',
        'post',
        {},
        'multipart/form-data',
        {'bbb': 1},
    )
    assert result['body_dict'] == {'bbb': 1}

    schema.validate_request(
        '/test_request_body',
        'post',
        {},
        'text/plain',
        None,
    )

    with pytest.raises(exceptions.MediaTypeNotAllowed):
        result = schema.validate_request(
            '/test_request_body',
            'post',
            {},
            'text/html',
            None,
        )

    with pytest.raises(exceptions.BodyValidationError):
        result = schema.validate_request(
            '/test_request_body',
            'post',
            {},
            'application/json',
            {},
        )
        result = schema.validate_request(
            '/test_request_body',
            'post',
            {},
            'application/json',
            {'aaa': 'ddd'},
        )


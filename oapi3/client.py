""" Module contains openapi3 client """
import json
import logging
import urllib.request
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlencode

from . import exceptions

logger = logging.getLogger()

DEFAULT_CLIENT_HEADERS = {
    'User-Agent': 'Mozilla/5.0',
}


def send_request(
    operation_id,
    url,
    operation,
    query,
    media_type=None,
    body=None,
    headers=None,
):
    if headers is None:
        headers = {}
    request_headers = DEFAULT_CLIENT_HEADERS.copy()
    request_headers.update(**headers)
    full_url = '{url}?{query}'.format(
        url=url,
        query=urlencode(query)
    )

    if body is not None:
        body = json.dumps(body).encode('utf-8')
    request = urllib.request.Request(
        full_url,
        data=body,
        headers=request_headers,
        method=operation.upper(),
    )
    if media_type:
        request.add_header("Content-Type", "application/json")
    try:
        response = urllib.request.urlopen(request)
    except HTTPError as e:
        logger.error('HTTPError for url: %s', full_url)
        logger.exception(e)
        raise exceptions.ApiRequestError(
            url,
            e.reason,
            getattr(e, 'code', 422),
            e.read(),
        ) from e
    except URLError as e:
        logger.error('URLError for url: %s', full_url)
        logger.exception(e)
        http_code = getattr(e, 'code', 503)
        raise exceptions.ApiRequestError(
            url,
            e.reason,
            http_code,
        ) from e
    return response.code, response.headers.get_content_type(), response.read()



class Operation:

    def __init__(self, client, pattern, operation, operation_id):
        self.client = client
        self.pattern = pattern
        self.operation = operation
        self.operation_id = operation_id
        schema = self.client._schema
        self.schema_path_params = schema.get_path_parameters(pattern)
        self.schema_query_params = schema.get_query_parameters(
            pattern,
            operation,
        )

    def __call__(self, params=None, media_type=None, body=None, headers=None):
        if not params:
            params = {}
        if headers is None:
            headers = {}
        path_params = {
            k: v for k, v in params.items()
            if k in self.schema_path_params
        }
        query_params = {
            k: v for k, v in params.items()
            if k in self.schema_query_params
        }

        self.client._schema.validate_parameters(
            self.schema_path_params,
            path_params,
        )
        self.client._schema.validate_parameters(
            self.schema_query_params,
            query_params,
        )
        query_params = self.client._schema.serialize_parameters(
            self.schema_query_params,
            query_params)

        path = str(self.pattern)
        for k, v in path_params.items():
            path = path.replace('{{{}}}'.format(k), str(v))
        url = self.client._url + path

        if media_type is None and body is not None:
            media_type = 'application/json'

        self.client._schema.validate_request(
            path,
            self.operation,
            query_params,
            media_type,
            body,
        )
        resp_code, resp_content_type, resp_content = self.client._send_request(
            self.operation_id,
            url,
            self.operation,
            query_params,
            media_type,
            body,
            headers,
        )
        if resp_content_type in (
                "application/x-www-form-urlencoded",
                "multipart/form-data",
        ):
            raise NotImplementedError
        elif resp_content_type == 'application/json':
            try:
                resp_body = json.loads(resp_content.decode())
            except (json.decoder.JSONDecodeError, ValueError) as exc:
                logging.info(body)
                raise exceptions.BodyValidationError(str(exc))
        else:
            resp_body = None
        return self.client._schema.validate_response(
            path,
            self.operation,
            resp_code,
            resp_content_type,
            resp_body,
        )


class Client:

    Operation = Operation

    def __init__(self, url, schema, send_request=send_request):
        self._url = url
        self._schema = schema
        self._send_request = send_request
        for path, path_obj in schema['paths'].items():
            for key, value in path_obj.items():
                if key in schema.METHODS:
                    operation_id = value['operationId']
                    op = self._create_operation(path, key, operation_id)
                    setattr(self, operation_id, op)

    def _create_operation(self, path, key, operation_id):
        return self.Operation(self, path, key, operation_id)



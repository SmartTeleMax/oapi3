'''
Handlers for iktomi

>>> from oapi3.iktomi HOpenApi3
>>> HOpenApi3('openapi3/api.yaml') | h_cases(...)

'''
from typing import Union
from typing import Optional
from typing import Any
import fnmatch
import json
import logging
import os
from itertools import chain

import webob
import iktomi.web
from iktomi.utils import VersionedStorage

from . import exceptions
from .resolve import open_schema
from .schema import Schema

logger = logging.getLogger()


class HOpenApi3(iktomi.web.WebHandler):
    ''' Oapi3 validation iktomi handler '''

    schema: Schema

    def __init__(self, schema: Union[str, Schema]):
        super().__init__()
        if isinstance(schema, str):
            self.schema = open_schema(schema)
        else:
            self.schema = schema

    def __call__(
        self,
        env: VersionedStorage,
        data: VersionedStorage,
    ) -> webob.Response:
        path = env._route_state.path
        operation = env.request.method.lower()
        try:
            body = self._get_request_body(env.request)
        except (exceptions.BodyValidationError) as exc:
            return self._return_error(
                webob.exc.HTTPBadRequest,
                'BodyValidationError',
                str(exc),
            )
        try:
            state = self.schema.validate_request(
                path=path,
                operation=operation,
                query=dict(env.request.GET),
                media_type=env.request.content_type,
                body=body,
            )
        except exceptions.PathNotFound as exc:
            return self._return_error(
                webob.exc.HTTPNotFound,
                'PathNotFound',
                str(exc),
            )
        except exceptions.PathParamValidationError as exc:
            return self._return_error(
                webob.exc.HTTPNotFound,
                'PathParamValidationError',
                str(exc),
            )
        except exceptions.OperationNotAllowed as exc:
            return self._return_error(
                webob.exc.HTTPMethodNotAllowed,
                'OperationNotAllowed',
                str(exc),
            )
        except exceptions.QueryParamValidationError as exc:
            return self._return_error(
                webob.exc.HTTPBadRequest,
                'QueryParamValidationError',
                str(exc),
            )
        except exceptions.OperationNotAllowed as exc:
            return self._return_error(
                webob.exc.HTTPMethodNotAllowed,
                'OperationNotAllowed',
                str(exc),
            )
        except exceptions.MediaTypeNotAllowed as exc:
            return self._return_error(
                webob.exc.HTTPUnsupportedMediaType,
                'MediaTypeNotAllowed',
                str(exc),
            )
        except exceptions.BodyValidationError as exc:
            return self._return_error(
                webob.exc.HTTPBadRequest,
                'BodyValidationError',
                str(exc),
            )

        env.openapi3_state = state
        response = self._next_handler(env, data)
        if response is None:
            return self._return_error(
                webob.exc.HTTPNotImplemented,
                'NotImplemented',
                '{} not implemented'.format(env.request.path),
            )

        self.schema.validate_response(
            path=path,
            operation=operation,
            status_code=str(response.status_code),
            media_type=response.content_type,
            body=self.get_response_body(response),
        )
        return response

    def _get_request_body(self, request: webob.Request) -> Optional[dict]:
        """
        Method for getting body from request

        Parameters
        ----------
        request : webob.Request
            instance of request

        Returns
        -------
        [dict or None]
            content of request
        """
        if request.content_type in (
                "application/x-www-form-urlencoded",
                "multipart/form-data",
        ):
            return dict(request.POST)

        if request.content_type == 'application/json':
            return self._get_json_body(request.text)
        return None

    def _get_response_body(self, response: webob.Response) -> Optional[dict]:
        """
        Method for getting body from response

        Parameters
        ----------
        response : webob.Response
            instance of response

        Returns
        -------
        [dict or None]
            content of response
        """
        if response.content_type == 'application/json':
            return self._get_json_body(response.text)
        return None

    def _get_json_body(self, text: str) -> Any:
        try:
            return json.loads(text)
        except (json.decoder.JSONDecodeError, TypeError) as exc:
            raise exceptions.BodyValidationError(str(exc))

    def _return_error(
        self,
        exc: webob.exc.HTTPException,
        error: str,
        message: str,
    ) -> webob.Response:
        json_data = json.dumps({
            'code': error,
            'message': message,
        })
        return webob.Response(
            json_data,
            status=exc.code,
            content_type="application/json",
            charset='utf8',
        )


class HOperation(iktomi.web.WebHandler):
    ''' Handler for matching oapi3 operation_id '''

    schema: Schema
    operation_id: str

    def __init__(self, schema: Schema, operation_id: str):
        super().__init__()
        self.schema = schema
        self.operation_id = operation_id
        assert self.schema.get_operation_by_id(operation_id), \
            'Unknown operation {}'.format(operation_id)

    def __call__(
        self,
        env: VersionedStorage,
        data: VersionedStorage,
    ) -> Optional[webob.Response]:
        if env.openapi3_state['operation_id'] == self.operation_id:
            return self._next_handler(env, data)
        return None

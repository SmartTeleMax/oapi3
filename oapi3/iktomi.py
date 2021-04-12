import fnmatch
import json
import logging
import os
from itertools import chain

import webob
import yaml
import iktomi.web

from . import exceptions
from .resolve import open_schema

logger = logging.getLogger()


class HOpenApi3(iktomi.web.WebHandler):

    def __init__(self, schema):
        super().__init__()
        if isinstance(schema, str):
            self.schema = open_schema(schema)
        else:
            self.schema = schema

    def _update_required(self, base_path, app_path, cache_path):
        if not os.path.isfile(cache_path):
            return True

        mtime = os.stat(cache_path).st_mtime
        paths = [os.path.dirname(app_path), base_path]

        for root, dirnames, filenames in chain.from_iterable(
                os.walk(path) for path in paths):
            for filename in fnmatch.filter(filenames, '*.yaml'):
                if mtime < os.stat(os.path.join(root, filename)).st_mtime:
                    return True
        return False

    def get_request_body(self, request):
        """
        Метод для извлечения "тела" из запроса.
        Мы загружаем файлы через multipart/form-data, а всё остальное у нас
        отправляется как application/json.
        В первом случае request.body будет пустым, нужные нам данные
        находятся в request.POST. Во втором случае всё наоборот - .POST пустой,
        а нужный нам json лежит в body. Для упрощения дальнейшей обработки
        запроса будем любые нужные нам данные называть термином body,
        возвращая нужный нам контент в этом методе.

        Parameters
        ----------
        request : webob.Request
            instance of request

        Returns
        -------
        [webob.Multidict or bytes]
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

    def get_response_body(self, response):
        """
        Метод для извлечения "тела" из ответа.

        Parameters
        ----------
        response : webob.Response
            instance of response

        Returns
        -------
        [webob.Multidict or bytes]
            content of response
        """
        if response.content_type == 'application/json':
            return self._get_json_body(response.text)
        return None

    def __call__(self, env, data):
        path = env._route_state.path
        operation = env.request.method.lower()
        try:
            body = self.get_request_body(env.request)
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

    def _get_json_body(self, text):
        try:
            return json.loads(text)
        except (json.decoder.JSONDecodeError, TypeError) as exc:
            raise exceptions.BodyValidationError(str(exc))

    def _return_error(self, exc, error, message):
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

    def __init__(self, schema, operation_id):
        super().__init__()
        self.schema = schema
        self.operation_id = operation_id
        assert self.schema.get_operation_by_id(operation_id), \
            'Unknown operation {}'.format(operation_id)

    def __call__(self, env, data):
        if env.openapi3_state['operation_id'] == self.operation_id:
            return self._next_handler(env, data)


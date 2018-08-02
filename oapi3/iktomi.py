import json
import logging
import iktomi.web
import webob

from . import from_yaml
from . import exceptions

logger = logging.getLogger()


class HOpenApi3(iktomi.web.WebHandler):

    def __init__(self, schema_path):
        super().__init__()
        with open(schema_path) as f:
            self.schema = from_yaml(
                f,
                schema_url='file://{}'.format(schema_path),
            )

    def __call__(self, env, data):
        try:
            state = self.schema.validate_request(
                path=env._route_state.path,
                operation=env.request.method.lower(),
                query=env.request.GET,
                media_type=env.request.content_type,
                body=env.request.body,
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
            request_state=state,
            status_code=str(response.status_code),
            media_type=response.content_type,
            body=response.body,
        )
        return response

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

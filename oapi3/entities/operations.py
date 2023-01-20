''' Module contains operation entity class '''
from typing import Dict

from oapi3 import exceptions

from .base import Entity
from .parameters import ParametersEntity
from .media_types import ContentEntity


METHODS = {
    'get',
    'put',
    'post',
    'delete',
    'options',
    'head',
    'patch',
    'trace',
}


class RequestBodyEntity(Entity):
    '''
    Request Body entity represents Request Body Object
    https://spec.openapis.org/oas/v3.1.0#request-body-object
    '''

    __slots__ = [
        'required',
        'media_types',
        'content',
    ]
    required: bool
    content: ContentEntity

    def __init__(self, request_body_obj: dict):
        super().__init__(request_body_obj)
        self.required = request_body_obj.get('required', False)
        self.content = ContentEntity(request_body_obj['content'])


class ResponseEntity(Entity):
    '''
    Response entity represents Responses Object
    https://spec.openapis.org/oas/v3.1.0#response-object
    '''
    __slots__ = ['content']
    content: ContentEntity

    def __init__(self, response_obj: dict):
        super().__init__(response_obj)
        content_obj = response_obj.get('content')
        if content_obj:
            self.content = ContentEntity(content_obj)
        else:
            self.content = None


class ResponsesEntity(Entity):
    '''
    Response entity represents Responses Object
    https://spec.openapis.org/oas/v3.1.0#responses-object
    '''
    __slots__ = [
        'default',
        'responses',
    ]

    def __init__(self, responses_obj: dict):
        super().__init__(responses_obj)
        default_obj = responses_obj.get('default')
        if default_obj is None:
            self.default = None
        else:
            self.default = ResponseEntity(default_obj) 
        self.responses = {
            k: ResponseEntity(v)
            for k, v in responses_obj.items() if k != 'default'
        }

    def match_status_code(self, status_code: int) -> ResponseEntity:
        ''' Match http response status code '''
        response = self.responses.get(str(status_code), self.default)
        if response:
            return response
        raise exceptions.ResponseCodeNotAllowed(
            str(status_code),
            list(self.responses),
        )

class OperationEntity(Entity):
    '''
    Operation entity represents Operation Object
    https://spec.openapis.org/oas/v3.1.0#operation-object
    '''

    __slots__ = [
        'operation',
        'operation_id',
        'parameters',
        'request_body',
        'responses',
    ]
    operation: str
    parameters: ParametersEntity
    request_body: RequestBodyEntity
    responses: ResponsesEntity

    def __init__(
        self,
        operation: str,
        operation_obj: dict,
        path_parameter_objs: list,
    ):
        super().__init__(operation_obj)
        self.operation = operation
        self.operation_id = operation_obj['operationId']

        operation_parameter_objs = operation_obj.get('parameters', [])
        parameter_objs = path_parameter_objs + operation_parameter_objs
        # parameters objs unique by "in" and "name" properties
        # replace path parameters by operation parameters
        unic_parameter_objs = {
            (p['in'], p['name']): p for p in parameter_objs
        }
        self.parameters = ParametersEntity(unic_parameter_objs.values())

        request_body_obj = operation_obj.get('requestBody')
        if request_body_obj is None:
            self.request_body = None
        else:
            self.request_body = RequestBodyEntity(request_body_obj)
        self.responses = ResponsesEntity(operation_obj.get('responses', {}))

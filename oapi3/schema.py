''' Module conatins Schema class '''
from typing import Any
import re
from collections import OrderedDict

from . import exceptions
from . import jsonschema_validator
from .entities import PathsEntity


class Schema(dict):
    ''' Schema for validating reauests and responses '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.paths_entity = PathsEntity(self['paths'])

    def validate_request(
        self,
        path: str,
        operation: str,
        query: dict,
        media_type: str,
        body: Any,
    ):
        ''' Validate request '''
        path_entity = self.paths_entity.match_path(path)
        path_params = path_entity.parse_path_parameters(path)

        operation_entity = path_entity.match_operation(operation)
        try:
            path_params = operation_entity.parameters.deserialize(
                'path',
                path_params,
            )
            operation_entity.parameters.validate('path', path_params)
        except (
                exceptions.SchemaValidationError,
                exceptions.ParameterTypeError,
        ) as exc:
            raise exceptions.PathParamValidationError(str(exc))

        try:
            query_params = operation_entity.parameters.deserialize(
                'query',
                query,
            )
            operation_entity.parameters.validate('query', query_params)
        except (
                exceptions.SchemaValidationError,
                exceptions.ParameterTypeError,
        ) as exc:
            raise exceptions.QueryParamValidationError(str(exc))

        if operation_entity.request_body:
            content = operation_entity.request_body.content
            media_type_entity = content.match_media_type(media_type)
            media_type_entity.validate_body(body)
            body_dict = media_type_entity.get_body_value(body)
        else:
            body_dict = {}
        return {
            'path': path,
            'operation': operation,
            'operation_id': operation_entity.operation_id,
            'query': query_params,
            'query_params_dict': query_params,
            'media_type': media_type,
            'body': body,
            'body_dict': body_dict,
            'path_params': path_params,
            'path_params_dict': path_params,
            'query_params': query_params,
        }

    def validate_response(
        self,
        path: str,
        operation: str,
        status_code: int,
        media_type: str,
        body: Any,
    ):
        ''' Validate http response '''
        path_entity = self.paths_entity.match_path(path)
        operation_entity = path_entity.match_operation(operation)

        response = operation_entity.responses.match_status_code(status_code)
        if response.content:
            media_type_entity = response.content.match_media_type(media_type)
            media_type_entity.validate_body(body)

        return {
            'path': path,
            'operation': operation,
            'media_type': media_type,
            'body': body,
        }

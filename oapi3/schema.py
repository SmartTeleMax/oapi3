import os
import re
import json
from urllib.parse import urlparse
from urllib.parse import urldefrag

import jsonschema
import openapi_spec_validator

from . import exceptions



class Object(dict):

    def __init__(self, root, value):
        self.root = root
        super().__init__(value)


class OpenApiObject(Object):

    def __init__(self, schema_dict, schema_url):
        openapi_spec_validator.validate_spec(schema_dict, spec_url=schema_url)
        assert schema_dict['openapi'] == '3.0'
        self.schema_dict = schema_dict
        base_url, referer = os.path.split(schema_url)
        self.ref_resolver = jsonschema.RefResolver(
            schema_url,
            schema_dict,
            handlers={
                'file': openapi_spec_validator.UrlHandler('file'),
            },
        )
        super().__init__(
            self,
            dict(
                openapi=schema_dict['openapi'],
                paths=PathsObject(self, schema_dict['paths']),
            ),
        )

    def validate_request(self, path, operation, query, media_type, body):
        path_obj = self['paths'].validate_request_path(path)
        path_params = path_obj.validate_request_path_params(path)
        operation_obj = path_obj.validate_request_operation(operation)
        query_params = operation_obj.validate_request_query(query)
        media_type_obj = operation_obj.validate_request_media_type(media_type)
        if media_type_obj:
            body_dict = media_type_obj.validate_body(body)
        else:
            body_dict = {}
        return {
            'path': path,
            'operation': operation,
            'query': query,
            'media_type': media_type,
            'body': body,
            'path_obj': path_obj,
            'path_params_dict': path_params,
            'operation_obj': operation_obj,
            'query_params_dict': query_params,
            'media_type_obj': media_type_obj,
            'body_dict': body_dict,
        }

    def validate_response(self, request_state, status_code, media_type, body):
        operation_obj = request_state['operation_obj']
        response_obj = operation_obj.validate_response_status_code(status_code)
        media_type_obj = response_obj.validate_response_media_type(media_type)
        if media_type_obj:
            body = media_type_obj.validate_body(body)
        else:
            body = None


def resolve_value(func):
    def wrapper(self, root, value, *args, **kwargs):
        if '$ref' in value:
            with root.ref_resolver.resolving(value['$ref']) as value:
                return func(self, root, value, *args, **kwargs)
        else:
            return func(self, root, value, *args, **kwargs)
    return wrapper


class PathsObject(Object):

    def __init__(self, root, value):
        super().__init__(
            root,
            {k: PathObject(root, v, k) for k, v in value.items()}
        )

    def validate_request_path(self, path):
        for k, v in self.items():
            if v.regex.match(path):
                return v
        else:
            raise exceptions.PathNotFound(path)


class PathObject(Object):

    OPERATIONS = ['get', 'put', 'post', 'delete', 'options', 'head', 'patch']


    @resolve_value
    def __init__(self, root, value, pattern):
        self.pattern = pattern
        self.path_param_names = re.findall('\{([0-9a-zA-Z_]+)\}', pattern)
        #XXX
        self.regex = re.compile(
            re.sub('\{[0-9a-zA-Z_]+\}', '([0-9a-zA-Z_\-]+)', pattern) + '$',
        )

        operations = {
            o: OperationObject(root, value[o], o) \
            for o in self.OPERATIONS if o in value
        }

        parameters = ParametersObject(root, value.get('parameters', []))

        super().__init__(
            root,
            dict(
                operations=operations,
                parameters=parameters,
            )
        )

    def validate_request_path_params(self, path):
        params = dict(zip(
            self.path_param_names,
            self.regex.match(path).groups(),
        ))
        try:
            params = self['parameters']['path'].deserialize(params)
        except exceptions.ParameterTypeError as exc:
            raise exceptions.PathParamValidationError(str(exc))
        try:
            self['parameters']['path'].validate(params)
        except exceptions.SchemaValidationError as exc:
            raise exceptions.PathParamValidationError(str(exc))
        return params

    def validate_request_operation(self, operation):
        if operation in self['operations']:
            return self['operations'][operation]
        else:
            raise exceptions.OperationNotAllowed(
                operation,
                list(self['operations']),
            )


class ParametersObject(Object):

    LOCATIONS = ["query", "path"]

    def __init__(self, root, value):
        if not value:
            value = []
        super().__init__(
            root,
            {
                l: ParametersListObject(root, value, l) \
                for l in self.LOCATIONS
            },
        )
        #for v in value:
        #    parameter = ParameterObject(root, v)
        #    self[parameter['in']][parameter['name']] = parameter


class ParametersListObject(Object):

    def __init__(self, root, value, location):
        params = [ParameterObject(root, p) for p in value]
        params = {p['name']: p for p in params if p['in']==location}
        super().__init__(root, params)
        self.schema = SchemaObject(
            root, 
            {
                'type': 'object',
                'additionalProperties': False,
                'properties': {k: self[k]['schema'] for k in self},
                'required': [k for k, v in self.items() if v['required']],
            },
        )

    def deserialize(self, value):
        result = {}
        for k, v in value.items():
            parameter_obj = self.get(k)
            if parameter_obj:
                result[k] = parameter_obj.deserialize(v)
            else:
                #XXX
                result[k] = v
        return result

    def validate(self, value):
        return self.schema.validate(value)


class ParameterObject(Object):

    @resolve_value
    def __init__(self, root, value):
        super().__init__(root, {
            'name': value['name'],
            'in': value['in'],
            'required': value.get('required', False),
            'schema': SchemaObject(root, value.get('schema')),
        })

    def deserialize(self, value):
        #XXX
        tp = self['schema'].get('type')
        if tp in ['integer', 'long', 'double']:
            try:
                return int(value)
            except ValueError:
                raise exceptions.ParameterTypeError(self['name'], value, tp)
        else:
            return value


class SchemaObject(Object):
    @resolve_value
    def __init__(self, root, value):
        super().__init__(root, value)
        self.resolver_scope = root.ref_resolver.resolution_scope
        self.validator = jsonschema.Draft4Validator(
            self,
            resolver=root.ref_resolver,
        )

    def validate(self, value):
        with self.validator.resolver.in_scope(self.resolver_scope):
            try:
                self.validator.validate(value)
            except jsonschema.exceptions.ValidationError as exc:
                raise exceptions.SchemaValidationError(exc.path, exc.message)


class OperationObject(Object):
    def __init__(self, root, value, operation):
        self.operation = operation
        super().__init__(
            root,
            {
                'parameters': ParametersObject(root, value.get('parameters')),
                'responses': ResponsesObject(root, value['responses'])
            }
        )
        requestBody = value.get('requestBody')
        if requestBody:
            self['requestBody'] = RequestBodyObject(root, requestBody)
        else:
            self['requestBody'] = None

    def validate_request_query(self, query):
        try:
            query = self['parameters']['query'].deserialize(query)
        except exceptions.ParameterTypeError as exc:
            raise exceptions.QueryParamValidationError(str(exc))
        try:
            self['parameters']['query'].validate(query)
        except exceptions.SchemaValidationError as exc:
            raise exceptions.QueryParamValidationError(str(exc))
        return query

    def validate_request_media_type(self, media_type):
        request_body_obj = self.get('requestBody')
        if request_body_obj:
            return request_body_obj.validate_media_type(media_type)
        else:
            return None

    def validate_response_status_code(self, status_code):
        return self['responses'].validate_status_code(status_code)


class RequestBodyObject(Object):

    @resolve_value
    def __init__(self, root, value):
        super().__init__(
            root,
            {
                'required': value.get('required', False),
                'content': {
                    k: MediaTypeObject(root, v, k) \
                    for k, v in value['content'].items()
                },
            },
        )

    def validate_media_type(self, media_type):
        media_type_obj = self['content'].get(media_type)
        if media_type_obj:
            return media_type_obj
        else:
            raise exceptions.MediaTypeNotAllowed(
                media_type,
                self['content'].keys(),
            )


class MediaTypeObject(Object):

    MEDIA_TYPES = {
        'text/plain': 'validate_plain_text',
        'application/json': 'validate_application_json',
        'audio/x-wav': 'validate_audio_x_wav',
    }

    def __init__(self, root, value, media_type):
        assert media_type in self.MEDIA_TYPES
        self.media_type = media_type
        super().__init__(root, {
            'schema': SchemaObject(root, value.get('schema', {})),
            'encoding': value.get('encoding'),
        })

    def validate_body(self, body):
        return getattr(self, self.MEDIA_TYPES[self.media_type])(body)

    def validate_plain_text(self, value):
        return {}

    def validate_application_json(self, value):
        try:
            value = json.loads(value.decode())
        except (json.decoder.JSONDecodeError, TypeError) as exc:
            raise exceptions.JsonDecodeError(str(exc))
        try:
            self['schema'].validate(value)
        except exceptions.SchemaValidationError as exc:
            raise exceptions.BodyValidationError(str(exc))
        return value

    def validate_audio_x_wav(self, value):
        return value


class ResponsesObject(Object):

    def __init__(self, root, value):
        super().__init__(
            root,
            {k: ResponseObject(root, v, k) for k, v in value.items()},
        )

    def validate_status_code(self, status_code):
        response_obj = self.get(status_code)
        if response_obj:
            return response_obj
        else:
            response_obj = self.get('default')
            if response_obj:
                return response_obj
            else:
                raise exceptions.ResponseCodeNotAllowed(status_code, list(self))


class ResponseObject(Object):

    @resolve_value
    def __init__(self, root, value, status_code):
        self.status_code = status_code
        super().__init__(root, {})
        content = value.get('content')
        if content:
            self['content'] = {
                k: MediaTypeObject(root, v, k) \
                for k, v in value['content'].items()
            }
        else:
            self['content'] = None

    def validate_response_media_type(self, media_type):
        if not self['content']:
            return None
        media_type_object = self['content'].get(media_type)
        if media_type_object:
            return media_type_object
        else:
            raise exceptions.MediaTypeNotAllowed(
                media_type,
                list(self['content']),
            )

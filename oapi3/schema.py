import re
from collections import OrderedDict

from . import exceptions
from . import jsonschema_validator


class Schema(dict):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        path_matchers = [(p, PathMatcher(p)) for p in self['paths']]
        path_matchers.sort(key=lambda x: x[1].parts)
        self.path_matchers = OrderedDict(path_matchers)

    def validate_request(self, path, operation, query, media_type, body):
        result = self.match_path(path)
        if result is None:
            raise exceptions.PathNotFound(path)
        pattern, path_params = result

        path_params_objs = self.get_path_parameters(pattern)
        try:
            path_params = self.deserialize_parameters(
                path_params_objs,
                path_params,
            )
            self.validate_parameters(path_params_objs, path_params)
        except (
                exceptions.SchemaValidationError,
                exceptions.ParameterTypeError,
        ) as exc:
            raise exceptions.PathParamValidationError(str(exc))

        operation_obj = self.match_operation(pattern, operation)

        query_param_objs = self.get_query_parameters(pattern, operation)
        try:
            query_params = self.deserialize_parameters(query_param_objs, query)
            self.validate_parameters(query_param_objs, query_params)
        except (
                exceptions.SchemaValidationError,
                exceptions.ParameterTypeError,
        ) as exc:
            raise exceptions.QueryParamValidationError(str(exc))

        media_type_obj = self.match_request_media_type(
            pattern,
            operation,
            media_type,
        )

        if media_type_obj and body is not None:
            self.validate_body(media_type_obj['schema'], body)

        body_dict = body if body is not None else {}
        return {
            'path': path,
            'operation': operation,
            'operation_id': operation_obj['operationId'],
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
            path,
            operation,
            status_code,
            media_type,
            body,
    ):
        result = self.match_path(path)
        if result is None:
            raise exceptions.PathNotFound(path)
        pattern, path_params = result
        self.match_operation(pattern, operation)

        response_obj = self.match_response_status_code(
            pattern,
            operation,
            status_code,
        )

        media_type_obj = self.match_response_media_type(
            response_obj,
            media_type,
        )
        if media_type_obj and body is not None:
            self.validate_body(media_type_obj['schema'], body)
        else:
            body = None
        return {
            'path': path,
            'operation': operation,
            'media_type': media_type,
            'body': body,
        }

    def validate_parameters(self, parameter_objs, parameters):
        """ Validate parameters dict by parameter_objs dict """
        parameters_schema = {
            'type': 'object',
            'additionalProperties': False,
            'properties': {
                k: v['schema'] for k, v in parameter_objs.items()
            },
        }
        required = [k for k, v in parameter_objs.items() if v.get('required')]
        if required:
            parameters_schema['required'] = required

        try:
            self.validate_jsonschema(parameters_schema, parameters)
        except jsonschema_validator.ValidationError as exc:
            raise exceptions.SchemaValidationError(
                exc.absolute_path,
                exc.message,
            )

    def validate_body(self, schema_obj, body):
        try:
            self.validate_jsonschema(schema_obj, body)
        except jsonschema_validator.ValidationError as exc:
            raise exceptions.BodyValidationError(
                str(
                    exceptions.SchemaValidationError(
                        exc.absolute_path,
                        exc.message,
                    ),
                ),
            )

    def validate_jsonschema(self, schema_obj, value):
        return jsonschema_validator.validate(value, schema_obj)

    def get_path_parameters(self, pattern):
        """ Get path parameters for path """
        return {
            p['name']: p for p in self['paths'][pattern].get('parameters', [])
            if p['in'] == 'path'
        }

    def get_query_parameters(self, pattern, operation):
        """ Get query parameters for operation """
        assert operation in self.METHODS, \
            'Unknown operation {}'.format(operation)
        path_obj = self['paths'][pattern]
        parameters = {
            p['name']: p for p in path_obj.get('parameters', [])
            if p['in'] == 'query'
        }
        parameters.update({
            p['name']: p for p in path_obj[operation].get('parameters', [])
            if p['in'] == 'query'
        })
        return parameters

    def match_path(self, path):
        for matcher in self.path_matchers.values():
            params = matcher.match(path)
            if params is not None:
                return (matcher.pattern, params)
        return None

    def match_operation(self, pattern, operation):
        path_obj = self['paths'][pattern]
        path_obj_operations = [m for m in path_obj if m in self.METHODS]
        if operation not in path_obj_operations:
            raise exceptions.OperationNotAllowed(
                operation,
                path_obj_operations,
            )
        return path_obj[operation]

    def match_request_media_type(self, pattern, operation, media_type):
        request_body_obj = self['paths'][pattern][operation].get('requestBody')
        if not request_body_obj:
            return
        media_type_obj = request_body_obj['content'].get(media_type)
        if media_type_obj:
            return media_type_obj
        else:
            raise exceptions.MediaTypeNotAllowed(
                media_type,
                request_body_obj['content'].keys(),
            )

    def match_response_status_code(self, pattern, operation, status_code):
        responses_obj = self['paths'][pattern][operation]['responses']
        response_obj = responses_obj.get(str(status_code))

        if response_obj is not None:
            return response_obj
        else:
            response_obj = responses_obj.get('default')
            if response_obj is not None:
                return response_obj
            else:
                raise exceptions.ResponseCodeNotAllowed(
                    str(status_code),
                    list(responses_obj),
                )

    def match_response_media_type(self, response_obj, media_type):
        content_map = response_obj.get('content')
        if content_map is None:
            return None
        media_type_obj = content_map.get(media_type)
        if media_type_obj:
            return media_type_obj
        else:
            raise exceptions.MediaTypeNotAllowed(
                media_type,
                content_map.keys(),
            )

    def serialize_parameters(self, parameter_objs, parameters):
        result = {}
        for key, value in parameters.items():
            param_obj = parameter_objs.get(key)
            if param_obj:
                param_type = param_obj['schema'].get('type')

                if param_type == 'array':
                    style, explode, _ = self._array_params(param_obj)
                    value = ArraysData(value, style, explode).serialize()
            result[key] = value
        return result

    def deserialize_parameters(self, parameter_objs, parameters):
        result = {}
        for key, value in parameters.items():
            param_obj = parameter_objs.get(key)
            if param_obj:
                # XXX tmp huck
                param_type = param_obj['schema'].get('type')

                if param_type == 'array':
                    style, explode, inner_type = self._array_params(param_obj)
                    value = ArraysData(
                        value, style, explode,
                        inner_type=inner_type, key=key
                    ).deserialize()
                else:
                    value = ArraysData.parse_primitive(key, value, param_type)

            result[key] = value
        return result

    def get_operation_by_id(self, operation_id):
        for pattern, operations in self['paths'].items():
            for method, operation in operations.items():
                if method not in self.METHODS:
                    continue
                if operation['operationId'] == operation_id:
                    return pattern, method, operation


    @staticmethod
    def _array_params(param_obj):
        style = param_obj.get('style', 'form')
        explode = param_obj.get('explode', style == 'form')
        inner_type = param_obj.get('schema') \
            .get('items').get('type')
        if not inner_type:
            inner_type = 'str'

        return style, explode, inner_type


class ArraysData:
    def __init__(self, data, style, explode: bool, **kwargs):
        self.data = data
        self.style = style
        self.explode = explode

        self.inner_type = kwargs.get('inner_type', None)
        self.key = kwargs.get('key', None)

    def serialize(self):
        method = getattr(self, 'serialize_{}{}_explode'.format(
            self.style.lower(), '_no' if not self.explode else ''))
        if method:
            return method()
        else:
            raise NotImplementedError(
                'serializing query parameter with style={} and explode={} is '
                'not implemented'.format(self.style, self.explode))

    def deserialize(self):
        method = getattr(self, 'deserialize_{}{}_explode'.format(
            self.style.lower(), '_no' if not self.explode else ''))
        if method:
            return method()
        else:
            raise NotImplementedError(
                'deserializing query parameter with '
                'style={} and explode={} is not implemented'
                .format(self.style, self.explode))

    def serialize_pipedelimited_no_explode(self):
        return '|'.join([str(v) for v in self.data])

    def serialize_spacedelimited_no_explode(self):
        return ' '.join([str(v) for v in self.data])

    def deserialize_pipedelimited_no_explode(self):
        return self._deserialize('|')

    def deserialize_spacedelimited_no_explode(self):
        return self._deserialize(' ')

    def _deserialize(self, delimiter):
        if self.data == '':
            return []
        return [self.parse_primitive('{}({})'.format(self.key, i),
                                     element, self.inner_type)
                for i, element in enumerate(self.data.split(delimiter))]

    @staticmethod
    def parse_primitive(key, value, type):
        if type in ['integer', 'long', 'double']:
            try:
                return int(value)
            except ValueError:
                raise exceptions.ParameterTypeError(
                    key,
                    value,
                    type,
                )
        return value


class PathMatcher:

    def __init__(self, pattern):
        self.pattern = pattern
        self.parts = pattern.split('/')[1:]
        self.parts_len = len(self.parts)
        self.path_param_names = re.findall(r'\{([0-9a-zA-Z_]+)\}', pattern)
        self.regex = re.compile(
            re.sub(
                r'\{[0-9a-zA-Z_]+\}',
                r'([0-9a-zA-Z_\-\.]+)',
                pattern,
            ) + '$',
        )

    def match(self, path):
        if not self.regex.match(path):
            return None
        return dict(zip(
            self.path_param_names,
            self.regex.match(path).groups(),
        ))

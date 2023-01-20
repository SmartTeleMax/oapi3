''' Module contain classes for serialize, deserialize and validate params '''
from typing import Any
from typing import Dict
import json
import abc

from oapi3 import exceptions
from oapi3 import jsonschema_validator

from .base import Entity


IMPLIMENTED_IN_VALUES = ['path', 'query']


class ParameterEntity(Entity):
    '''
    Parameter Entity represents Parameter Object
    https://spec.openapis.org/oas/v3.1.0#parameter-object
    '''

    __slots__ = [
        'required',
        'schema',
    ]
    required: bool
    schema: dict

    def __init__(self, parameter_obj: dict):
        super().__init__(parameter_obj)
        self.required = parameter_obj.get('required', False)
        self.schema = self._schema()

    @abc.abstractmethod
    def serialize(self, value: Any) -> str:
        ''' Serialize value '''

    @abc.abstractmethod
    def deserialize(self, value: str) -> Any:
        ''' Deserialize value '''

    @abc.abstractmethod
    def _schema(self) -> dict:
        ''' Get or create schema '''


class JsonParamSchema(ParameterEntity):
    ''' Parameter entity for params with conent type 'application/json' '''

    def serialize(self, value: Any) -> str:
        return json.dumps(value)

    def deserialize(self, value: str) -> Any:
        try:
            return json.loads(value)
        except json.decoder.JSONDecodeError as exc:
            raise exceptions.ParameterTypeError(
                self.obj['name'],
                value,
                'application/json',
            ) from exc

    def _schema(self) -> dict:
        content_type_obj = self.obj['content']['application/json']
        return content_type_obj.get('schema', {})


class PrimitiveParameterEntity(ParameterEntity):
    ''' Parameter entity for simple parameters '''

    def serialize(self, value: Any) -> str:
        return str(value)

    def deserialize(self, value: str) -> Any:
        return value

    def _schema(self) -> dict:
        return self.obj.get('schema', {})


class StringParameterEntity(PrimitiveParameterEntity):
    ''' Parameter entity for simple string parameters '''


class IntegerParameterEntity(PrimitiveParameterEntity):
    ''' Parameter entity for simple integer parameters '''

    def deserialize(self, value: str) -> Any:
        try:
            return int(value)
        except ValueError:
            # Not raise exception. It will be raised in schema validation.
            return value


class ArrayParameterEntity(PrimitiveParameterEntity):
    ''' Base parameter entity class for array parameters '''

    __slots__ = [
        'inner_schema',
    ]
    inner_schema: dict

    def __init__(self, parameter_obj: str):
        super().__init__(parameter_obj)
        inner_schema_obj = self.schema.get('items', {})
        inner_type = inner_schema_obj.get('type')
        self.inner_schema = PRIMITIVE_SCHEMAS[inner_type](
            {
                'name': {'{}[]'.format(self.obj['name'])},
                'in': None,
                'schema': inner_schema_obj,
            },
        )


class DelemitedArrayParameterEntity(ArrayParameterEntity):
    ''' Base parameter entity for delimitted array parameter '''

    @property
    @abc.abstractmethod
    def delimiter(self) -> str:
        ''' Array delimiter '''

    def serialize(self, value: Any) -> str:
        return self.delimiter.join(
            [self.inner_schema.serialize(item) for item in value],
        )

    def deserialize(self, value: str) -> Any:
        if not value:
            return []
        return [
            self.inner_schema.deserialize(item)
            for item in value.split(self.delimiter)
        ]


class FormNEArrayEntity(DelemitedArrayParameterEntity):
    ''' Parameter entity for form not explode array parameters '''
    delimiter = ','


class PipedelimitedNEArrayEntity(DelemitedArrayParameterEntity):
    ''' Parameter entity for pipedelimited not explode array parameters '''
    delimiter = '|'


class SpacedelimitedNEArrayEntity(DelemitedArrayParameterEntity):
    ''' Parameter entity for pipedelimited not explode array parameters '''
    delimiter = ' '


CONTENT_PARAM_TYPES = {
    'application/json': JsonParamSchema,
}

PRIMITIVE_SCHEMAS = {
    None: PrimitiveParameterEntity,
    'string': StringParameterEntity,
    'integer': IntegerParameterEntity,
    'long': IntegerParameterEntity,
    'double': IntegerParameterEntity,
}

ARRAY_SCHEMAS = {
    ('form', False): FormNEArrayEntity,
    ('pipedelimited', False): PipedelimitedNEArrayEntity,
    ('spacedelimited', False): SpacedelimitedNEArrayEntity,
}

IMPLEMENTED_PARAM_TYPES = {
    ('path', 'simple', False): list(PRIMITIVE_SCHEMAS),
    ('query', 'form', True): list(PRIMITIVE_SCHEMAS),
    ('query', 'form', False): list(PRIMITIVE_SCHEMAS) + ['array'],
    ('query', 'pipedelimited', False): ['array'],
    ('query', 'spacedelimited', False): ['array'],
}


def create_parameter_entity(parameter_obj: dict) -> ParameterEntity:
    ''' Create param schema by param_obj '''
    if 'content' in parameter_obj:
        return _create_parameter_entity_by_content(parameter_obj)
    return _create_parameter_entity_by_schema(parameter_obj)


def _create_parameter_entity_by_content(parameter_obj: str) -> ParameterEntity:
    content_type = next(iter(parameter_obj['content']), None)
    schema_cls = CONTENT_PARAM_TYPES.get(content_type)
    if not schema_cls:
        raise NotImplementedError(
            'Unknown param content_type {}'.format(content_type),
        )
    return schema_cls(parameter_obj)


def _create_parameter_entity_by_schema(parameter_obj: str) -> ParameterEntity:
    schema = parameter_obj.get('schema', {})
    parameter_type = schema.get('type')
    # https://spec.openapis.org/oas/latest.html#parameter-object
    if 'style' in parameter_obj:
        style = parameter_obj['style']
    elif parameter_obj['in'] == 'path':
        style = 'simple'
    elif parameter_obj['in'] == 'query':
        style = 'form'
    if 'explode' in parameter_obj:
        explode = parameter_obj['explode']
    elif style == 'form':
        explode = True
    else:
        explode = False

    implemented_types = IMPLEMENTED_PARAM_TYPES.get(
        (parameter_obj['in'], style, explode),
        [],
    )
    if parameter_type not in implemented_types:
        raise NotImplementedError(
            'Param name={} in={} style={} explode={} type={}'.format(
                parameter_obj['name'],
                parameter_obj['in'],
                style,
                explode,
                parameter_type,
            ),
        )
    if parameter_type in PRIMITIVE_SCHEMAS:
        return PRIMITIVE_SCHEMAS[parameter_type](parameter_obj)
    if parameter_type == 'array':
        inner_type = parameter_obj['schema'].get('itmes', {}).get('type')
        if inner_type not in PRIMITIVE_SCHEMAS:
            raise NotImplementedError(
                'Param name={}: inner type {} not implemented'.format(
                    parameter_obj['name'],
                    inner_type,
                ),
            )
        return ARRAY_SCHEMAS[(style, explode)](parameter_obj)


class ParametersEntity(Entity):
    '''
    Parameters Entity represents parameters list in
    PathObject or OperationObject
    https://spec.openapis.org/oas/v3.1.0#path-item-object
    https://spec.openapis.org/oas/v3.1.0#operation-object
    '''

    __slots__ = ['parameters', 'schema']
    parameters: Dict[str, ParameterEntity]
    schema: Dict[str, dict]

    def __init__(self, parameter_objs: list):
        super().__init__(parameter_objs)
        self.parameters = {in_: {} for in_ in IMPLIMENTED_IN_VALUES}
        for p in parameter_objs:
            if p['in'] not in IMPLIMENTED_IN_VALUES:
                continue
            self.parameters[p['in']][p['name']] = create_parameter_entity(p)
        self.schema = {in_: self._schema(in_) for in_ in IMPLIMENTED_IN_VALUES}

    def deserialize(self, in_: str, values: Dict[str, str]) -> Dict[str, Any]:
        ''' Deserialize parameters '''
        if in_ not in IMPLIMENTED_IN_VALUES:
            raise NotImplementedError(in_)
        return dict(
            values,
            **{
                k: self.parameters[in_][k].deserialize(v)
                for k, v in values.items()
                if k in self.parameters[in_]
            }
        )

    def serialize(self, in_: str, values: Dict[str, Any]) -> Dict[str, str]:
        ''' Serialize parameters '''
        if in_ not in IMPLIMENTED_IN_VALUES:
            raise NotImplementedError(in_)
        return dict(
            values,
            {
                k: self.parameters[in_][k].serialize(v)
                for k, v in values.items()
                if k in self.parameters[in_]
            }
        )

    def validate(self, in_: str, values: Dict[str, Any]):
        """ Validate parameters dict by parameter_objs dict """
        if in_ not in IMPLIMENTED_IN_VALUES:
            raise NotImplementedError(in_)
        try:
            jsonschema_validator.validate(values, self.schema[in_])
        except jsonschema_validator.ValidationError as exc:
            raise exceptions.SchemaValidationError(
                exc.absolute_path,
                exc.message,
            )

    def _schema(self, in_: str) -> dict:
        schema = {
            'type': 'object',
            'additionalProperties': False,
            'properties': {
                k: v.schema for k, v in self.parameters[in_].items()
            }
        }
        required = [k for k, v in self.parameters[in_].items() if v.required]
        if required:
            schema['required'] = required
        return schema

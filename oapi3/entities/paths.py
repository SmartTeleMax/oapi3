''' Module contain PathEntity and PathEntity classes '''
from typing import List
from typing import Dict
import re

from oapi3 import exceptions

from .base import Entity
from .parameters import ParametersEntity
from .operations import OperationEntity
from .operations import METHODS


class PathEntity(Entity):
    '''
    Path Entity represents Path Object
    https://spec.openapis.org/oas/v3.1.0#path-item-object
    '''

    __slots__ = [
        'parts',
        'pattern',
        'path_param_names',
        'regex',
        'parameters',
        'operations',
    ]
    parts: List[str]
    pattern: str
    path_param_names: List[str]
    regex: re.Pattern
    operations: Dict[str, OperationEntity]

    def __init__(self, pattern: str, path_obj: dict):
        super().__init__(path_obj)
        self.pattern = pattern
        self.parts = pattern.split('/')[1:]
        self.path_param_names = re.findall(r'\{([0-9a-zA-Z_]+)\}', pattern)
        self.regex = re.compile(
            re.sub(
                r'\{[0-9a-zA-Z_]+\}',
                r'([0-9a-zA-Z_\-\.]+)',
                pattern,
            ) + '$',
        )
        self.operations = {
            k: OperationEntity(k, v, path_obj.get('parameters', []))
            for k, v in path_obj.items() if k in METHODS
        }

    def match(self, path: str) -> bool:
        ''' Match path '''
        return self.regex.match(path)

    def parse_path_parameters(self, path: str) -> dict:
        ''' Get path parameters from path '''
        return dict(zip(
            self.path_param_names,
            self.regex.match(path).groups(),
        ))

    def match_operation(self, operation: str) -> OperationEntity:
        ''' Match http operation(method) '''
        operation_entity = self.operations.get(operation)
        if operation_entity:
            return operation_entity
        raise exceptions.OperationNotAllowed(
            operation,
            list(self.operations.keys()),
        )


class PathsEntity(Entity):
    '''
    Paths Entity represents Paths Object 
    https://spec.openapis.org/oas/v3.1.0#paths-object
    '''

    __slots__ = [
        'paths',
    ]
    paths: List[PathEntity]

    def __init__(self, paths_obj: dict):
        super().__init__(paths_obj)
        self.paths = [PathEntity(k, v) for k, v in paths_obj.items()]
        self.paths.sort(key=lambda x: x.parts)

    def match_path(self, path: str) -> PathEntity:
        ''' Match path '''
        for path_entity in self.paths:
            if path_entity.match(path):
                return path_entity
        raise exceptions.PathNotFound(path)

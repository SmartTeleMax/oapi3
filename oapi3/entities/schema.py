''' Module contains schema entity '''
from typing import Any

from oapi3 import exceptions
from oapi3 import jsonschema_validator
from .base import Entity


class SchemaEntity(Entity):
    '''
    Schema entity represents Schema Object
    https://spec.openapis.org/oas/v3.1.0#schema-object
    '''

    def validate(self, value: Any):
        try:
            jsonschema_validator.validate(value, self.obj)
        except jsonschema_validator.ValidationError as exc:
            raise exceptions.BodyValidationError(
                str(
                    exceptions.SchemaValidationError(
                        exc.absolute_path,
                        exc.message,
                    ),
                ),
            )

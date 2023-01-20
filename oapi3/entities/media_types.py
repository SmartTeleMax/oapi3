''' Module contains Media Type enitities classes '''
from typing import Any
from typing import Dict

from oapi3 import exceptions

from .base import Entity
from .schema import SchemaEntity


class MediaTypeEntity(Entity):
    '''
    Media Type entity represents MediaType Object
    https://spec.openapis.org/oas/v3.1.0#mediaTypeObject
    '''
    def validate_body(self, value: Any):
        ''' Validate value '''

    def get_body_value(self, value: Any):
        return {}


class MediaTypeWithSchema(MediaTypeEntity):
    '''
    Media Type entity represents MediaType Object with
    application/json media type
    '''

    __slots__ = [
        'schema',
    ]
    schema: SchemaEntity

    def __init__(self, media_type_obj: dict):
        super().__init__(media_type_obj)
        self.schema = SchemaEntity(media_type_obj.get('schema', {}))

    def validate_body(self, value: Any):
        ''' Validate value '''
        self.schema.validate(value)

    def get_body_value(self, value: Any):
        return value


MEDIA_TYPES = {
    'application/json': MediaTypeWithSchema,
    'application/x-www-form-urlencoded': MediaTypeWithSchema,
    'multipart/form-data': MediaTypeWithSchema,
}


def create_media_type_entity(media_type: str, media_type_obj: dict):
    ''' Create media type entity '''
    cls = MEDIA_TYPES.get(media_type, MediaTypeEntity)
    return cls(media_type_obj)


class ContentEntity(Entity):
    '''
    MedaiTypes entity represents content property of RequestBody Object
    or ResponseObject 
    https://spec.openapis.org/oas/v3.1.0#request-body-object
    https://spec.openapis.org/oas/v3.1.0#response-object
    '''

    __slots__ = [
        'media_types',
    ]
    media_types: Dict[str, MediaTypeEntity]

    def __init__(self, media_type_objs: dict):
        super().__init__(media_type_objs)
        self.media_types = {
            tuple(k.split('/')): create_media_type_entity(k, media_type_objs[k])
            for k in sorted(media_type_objs, reverse=True)
        }

    def match_media_type(self, media_type: str) -> MediaTypeEntity:
        ''' Match request media type '''
        media_type_parts = media_type.split('/')
        if len(media_type_parts) == 2:
            print(media_type_parts)
            for k, v in self.media_types.items():
                if k[0] != '*' and media_type_parts[0] != k[0]:
                    continue
                if k[1] != '*' and media_type_parts[1] != k[1]:
                    continue
                return v 
        raise exceptions.MediaTypeNotAllowed(
            media_type,
            ['/'.join(k) for k in self.media_types],
        )

import jsonschema._utils
import jsonschema._validators
import jsonschema.validators
from jsonschema.exceptions import SchemaError
from jsonschema.exceptions import ValidationError

draft_openapi3_meta_schema = jsonschema._utils.load_schema("draft4")
draft_openapi3_meta_schema['properties']['discriminator'] = {
    'type': 'object',
    'properties': {
        'propertyName': {'type': 'string'},
        'mapping': {'type': 'object'},
    },
    'required': ['propertyName', 'mapping'],
}


def discriminator_validator(validator, oneOf, instance, schema):
    discriminator = schema.get('discriminator')
    propertyName = discriminator['propertyName']
    mapping = discriminator['mapping']
    errs = list(validator.descend(
        instance,
        {
            'type': 'object',
            'properties': {
                propertyName: {
                    'type': 'string',
                    'enum': list(mapping),
                },
            },
            'required': [propertyName],
        },
    ))
    if errs:
        yield errs[0]
        return

    descr_value = instance[propertyName]
    descr_schema = mapping[descr_value]

    for index, subschema in enumerate(oneOf):
        if subschema == descr_schema:
            break
    else:
        yield SchemaError('descriminator error')
        return

    yield from validator.descend(instance, subschema, schema_path=index)


def oneOf_draft_openapi3(validator, oneOf, instance, schema):
    if 'discriminator' in schema:
        yield from discriminator_validator(validator, oneOf, instance, schema)
    else:
        yield from jsonschema._validators.oneOf(
            validator,
            oneOf,
            instance,
            schema,
        )


# XXX: hack: skip recursive refs
def ref_openapi3(validator, ref, instance, schema):
    if isinstance(instance, dict):
        items = instance.get('items', {})
        if isinstance(items, dict):
            properties = items.get('properties', {}).values()
            if instance not in properties:
                return jsonschema._validators.ref(validator, ref,
                                                  instance, schema)



validators = jsonschema.validators.Draft4Validator.VALIDATORS.copy()
validators['$ref'] = ref_openapi3
validators['oneOf'] = oneOf_draft_openapi3

DraftOpenapi3 = jsonschema.validators.create(
    meta_schema=draft_openapi3_meta_schema,
    validators=validators,
    version="draft_openapi3",
)


def validate(instance, schema):
    return jsonschema.validate(instance, schema, DraftOpenapi3)

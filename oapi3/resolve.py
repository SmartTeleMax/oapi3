"""
Module contains functions for open and resolve yaml schema files

Exemple:

    schema = open_schema('api.yaml')

"""
import os
from urllib.parse import urljoin
from urllib.parse import urlparse

import yaml

from .schema import Schema


def open_schema(root_file_path):
    """ Open schema """
    root_file_path = os.path.abspath(root_file_path)
    schema = {}
    open_schema_file(schema, root_file_path)
    resolve_value(schema, root_file_path, schema[root_file_path], {})
    return Schema(schema[root_file_path])


def open_schema_file(schema, file_path):
    """ Open and parse schema file. Function open recuesive other files,
    if the file contains refs.
    """
    if file_path in schema:
        return schema
    with open(file_path, encoding='utf-8') as f:
        value = yaml.load(f, Loader=yaml.SafeLoader)
    schema[file_path] = value
    ref_files = {ref[0] for ref in get_refs(schema, file_path, value)}
    for ref_file_path in ref_files:
        open_schema_file(schema, ref_file_path)
    return schema


def get_refs(schema, base_path, value):
    """ Get all refs from value """
    result = set()
    if isinstance(value, dict):
        for k, v in value.items():
            if k == '$ref':
                result.add(create_ref(base_path, v))
            else:
                result |= get_refs(schema, base_path, v)
        # resolve discriminator mapping
        if 'mapping' in value and isinstance(value['mapping'], dict):
            result |= {
                create_ref(base_path, v) for v in value['mapping'].values()
            }
    if isinstance(value, list):
        for i in value:
            result |= get_refs(schema, base_path, i)
    return result


def resolve_ref(schema, ref, cache):
    """ Get and resolve value referenced by ref """
    if ref in cache:
        return cache[ref]
    value = get_value_by_ref(schema, ref)
    if value is None:
        return None
    resolve_value(schema, ref[0], value, cache)
    cache[ref] = value
    return value


def resolve_value(schema, file_path, value, cache):
    """ Recurcive find and replace $ref in value """
    if isinstance(value, dict):
        resolved_keys = set()
        if '$ref' in value:
            ref = value.pop('$ref')
            ref_value = resolve_ref(
                schema,
                create_ref(file_path, ref),
                cache,
            )
            if ref_value is None:
                raise Exception(
                    'Ref not found file={}, ref={}'.format(file_path, ref),
                )
            resolved_keys = set(ref_value) - set(value)
            value.update(dict(ref_value, **value))
        # resolve discriminator mapping
        if 'mapping' in value and isinstance(value['mapping'], dict):
            for k, v in value['mapping'].items():
                if isinstance(v, str):  # XXX
                    value['mapping'][k] = resolve_ref(
                        schema,
                        create_ref(file_path, v),
                        cache,
                    )
        for k, v in value.items():
            if k in resolved_keys:
                continue
            if isinstance(v, (list, dict)):
                resolve_value(schema, file_path, v, cache)
    if isinstance(value, list):
        for i in value:
            if isinstance(i, (list, dict)):
                resolve_value(schema, file_path, i, cache)


def get_value_by_ref(schema, ref):
    """ Get value referenced by ref """
    value = schema.get(ref[0])
    if value is None:
        return None
    for key in ref[1].split('/')[1:]:
        try:
            value = value[key]
        except KeyError as exc:
            raise Exception(
                'Ref "{}" not found in file "{}"'.format(ref[1][1:], ref[0]),
            ) from exc
        if value is None:
            return None
    return value


def create_ref(file_path, ref_str):
    """ Create ref obj from ref string """
    ref = urlparse(ref_str)
    assert ref.fragment and not ref.netloc and not ref.query, \
        "Cannot resolve ref: {}".format(ref_str)
    if ref.path:
        path = os.path.normpath(
            os.path.join(
                os.path.dirname(file_path),
                os.path.normcase(ref.path),
            ),
        )
    else:
        path = file_path
    return path, ref.fragment

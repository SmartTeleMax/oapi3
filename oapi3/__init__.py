import json
import yaml
from .schema import OpenApiObject
from . import exceptions

def from_dict(d, schema_url):
    return OpenApiObject(d, schema_url=schema_url)

def from_yaml(f, schema_url):
    return from_dict(yaml.load(f), schema_url=schema_url)

def from_json(f, schema_url):
    return from_dict(json.load(f), schema_url=schema_url)


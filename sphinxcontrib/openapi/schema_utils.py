"""OpenAPI schema utility functions."""
import collections
import copy
from io import StringIO

import deepmerge

# collections.Mapping has been moved to `collections.abc.Mapping` in python 3.10
from jsonpointer import resolve_pointer

try:
    Mapping = collections.abc.Mapping
except AttributeError:
    Mapping = collections.Mapping

_DEFAULT_EXAMPLES = {
    "string": "string",
    "integer": 1,
    "number": 1.0,
    "boolean": True,
    "array": [],
}


_DEFAULT_STRING_EXAMPLES = {
    "date": "2020-01-01",
    "date-time": "2020-01-01T01:01:01Z",
    "password": "********",
    "byte": "QG1pY2hhZWxncmFoYW1ldmFucw==",
    "ipv4": "127.0.0.1",
    "ipv6": "::1",
}


def example_from_schema(schema):
    """
    Generates an example request/response body from the provided schema.

    >>> schema = {
    ...     "type": "object",
    ...     "required": ["id", "name"],
    ...     "properties": {
    ...         "id": {
    ...             "type": "integer",
    ...             "format": "int64"
    ...         },
    ...         "name": {
    ...             "type": "string",
    ...             "example": "John Smith"
    ...         },
    ...         "tag": {
    ...             "type": "string"
    ...         }
    ...     }
    ... }
    >>> example = example_from_schema(schema)
    >>> assert example == {
    ...     "id": 1,
    ...     "name": "John Smith",
    ...     "tag": "string"
    ... }
    """
    # If an example was provided then we use that
    if "example" in schema:
        return schema["example"]

    elif "oneOf" in schema:
        return example_from_schema(schema["oneOf"][0])

    elif "anyOf" in schema:
        return example_from_schema(schema["anyOf"][0])

    elif "allOf" in schema:
        # Combine schema examples
        example = {}
        for sub_schema in schema["allOf"]:
            example.update(example_from_schema(sub_schema))
        return example

    elif "enum" in schema:
        return schema["enum"][0]

    elif "type" not in schema and not "properties" in schema and "items" not in schema:
        # Any type
        return _DEFAULT_EXAMPLES["integer"]

    elif "properties" in schema or schema.get("type") == "object":
        example = {}
        for prop, prop_schema in schema.get("properties", {}).items():
            example[prop] = example_from_schema(prop_schema)
        return example

    elif "items" in schema or schema.get("type") == "array":
        items = schema["items"]
        min_length = schema.get("minItems", 0)
        max_length = schema.get("maxItems", max(min_length, 2))
        assert min_length <= max_length
        # Try generate at least 2 example array items
        gen_length = min(2, max_length) if min_length <= 2 else min_length

        example_items = []
        if items == {}:
            # Any-type arrays
            example_items.extend(_DEFAULT_EXAMPLES.values())
        elif isinstance(items, dict) and "oneOf" in items:
            # Mixed-type arrays
            example_items.append(_DEFAULT_EXAMPLES[sorted(items["oneOf"])[0]])
        else:
            example_items.append(example_from_schema(items))

        # Generate array containing example_items and satisfying min_length and max_length
        return [example_items[i % len(example_items)] for i in range(gen_length)]

    elif schema["type"] == "string":
        example_string = _DEFAULT_STRING_EXAMPLES.get(
            schema.get("format", None), _DEFAULT_EXAMPLES["string"]
        )
        min_length = schema.get("minLength", 0)
        max_length = schema.get("maxLength", max(min_length, len(example_string)))
        gen_length = (
            min(len(example_string), max_length)
            if min_length <= len(example_string)
            else min_length
        )
        assert 0 <= min_length <= max_length
        if min_length <= len(example_string) <= max_length:
            return example_string
        else:
            example_builder = StringIO()
            for i in range(gen_length):
                example_builder.write(example_string[i % len(example_string)])
            example_builder.seek(0)
            return example_builder.read()

    elif schema["type"] in ("integer", "number"):
        example = _DEFAULT_EXAMPLES[schema["type"]]
        if "minimum" in schema and "maximum" in schema:
            # Take average
            example = schema["minimum"] + (schema["maximum"] - schema["minimum"]) / 2
        elif "minimum" in schema and example <= schema["minimum"]:
            example = schema["minimum"] + 1
        elif "maximum" in schema and example >= schema["maximum"]:
            example = schema["maximum"] - 1
        return float(example) if schema["type"] == "number" else int(example)

    else:
        return _DEFAULT_EXAMPLES[schema["type"]]


_merge_mappings = deepmerge.Merger(
    [(Mapping, deepmerge.strategy.dict.DictStrategies("merge"))],
    ["override"],
    ["override"],
).merge


def _get_schema_type(schema):
    """Retrieve schema type either by reading 'type' or guessing."""

    # There are a lot of OpenAPI specs out there that may lack 'type' property
    # in their schemas. I fount no explanations on what is expected behaviour
    # in this case neither in OpenAPI nor in JSON Schema specifications. Thus
    # let's assume what everyone assumes, and try to guess schema type at least
    # for two most popular types: 'object' and 'array'.
    if "type" not in schema:
        if "properties" in schema:
            schema_type = "object"
        elif "items" in schema:
            schema_type = "array"
        else:
            schema_type = None
    else:
        schema_type = schema["type"]
    return schema_type


def traverse_schema(top_level, block, name, is_required=False):
    schema_type = _get_schema_type(block)
    if "$ref" in block:
        yield from traverse_schema(
            top_level,
            resolve_reference(top_level, block["$ref"]),
            name,
            is_required,
        )
    elif {"oneOf", "anyOf", "allOf"} & block.keys():
        # Since an item can represented by either or any schema from
        # the array of schema in case of `oneOf` and `anyOf`
        # respectively, the best we can do for them is to render the
        # first found variant. In other words, we are going to traverse
        # only a single schema variant and leave the rest out. This is
        # by design and it was decided so in order to keep produced
        # description clear and simple.
        yield from traverse_schema(
            top_level, resolve_combining_schema(block), name
        )
    elif "not" in block:
        yield name, {}, is_required
    elif schema_type == "object":
        if name:
            yield name, block, is_required

        required = set(block.get("required", []))

        for key, value in block.get("properties", {}).items():
            # In case of the first recursion call, when 'name' is an
            # empty string, we should go with 'key' only in order to
            # avoid leading dot at the beginning.
            yield from traverse_schema(
                top_level,
                value,
                f"{name}.{key}" if name else key,
                is_required=key in required,
            )
    elif schema_type == "array":
        yield from traverse_schema(top_level, block["items"], f"{name}[]")

    elif "enum" in block:
        yield name, block, is_required

    elif schema_type is not None:
        yield name, block, is_required


def resolve_combining_schema(schema):
    if "oneOf" in schema:
        # The part with merging is a vague one since I only found a
        # single 'oneOf' example where such merging was assumed, and no
        # explanations in the spec itself.
        merged_schema = schema.copy()
        merged_schema.update(merged_schema.pop("oneOf")[0])
        return merged_schema

    elif "anyOf" in schema:
        # The part with merging is a vague one since I only found a
        # single 'oneOf' example where such merging was assumed, and no
        # explanations in the spec itself.
        merged_schema = schema.copy()
        merged_schema.update(merged_schema.pop("anyOf")[0])
        return merged_schema

    elif "allOf" in schema:
        # Since the item is represented by all schemas from the array,
        # the best we can do is to render them all at once
        # sequentially. Please note, the only way the end result will
        # ever make sense is when all schemas from the array are of
        # object type.
        merged_schema = schema.copy()
        for item in merged_schema.pop("allOf"):
            merged_schema = _merge_mappings(merged_schema, copy.deepcopy(item))
        return merged_schema

    elif "not" in schema:
        # Eh.. do nothing because I have no idea what can we do.
        return {}

    return schema


def rebuild_references(top_level, block):
    schema_type = _get_schema_type(block)
    if schema_type == "object":
        if "properties" in block:
            properties = {}
            for k, v in block["properties"].items():
                properties[k] = rebuild_references(top_level, v)
            return {**block, "properties": properties}
        else:
            return block
    elif schema_type == "array":
        return {
            **block,
            "items": rebuild_references(top_level, block["items"])
        }
    elif {"oneOf", "anyOf", "allOf"} & block.keys():
        return rebuild_references(
            top_level, resolve_combining_schema(block),
        )
    elif "$ref" in block:
        return rebuild_references(
            top_level, resolve_reference(top_level, block["$ref"])
        )
    else:
        return block


def resolve_reference(schema, link):
    if link.startswith("#"):
        return resolve_pointer(schema, link[1:]).copy()
    else:
        raise NotImplementedError("Resolving references to URIs is not currently supported.")

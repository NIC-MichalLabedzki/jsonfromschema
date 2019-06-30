import json
import math
import os
import sys
import pprint


def generate_type(root_dir, schema_root, section, verbose=False):
    def get_local_schema(schema_file, verbose=False):
        with open(schema_file, 'r') as input:
            schema = json.load(input)
            if verbose:
                print('>>> Schema[{}] is:'.format(schema_file))
                pprint.pprint(schema)
            input.close()
        return schema

    def get_section_from_fragment_path(where, schema):
        i_schema = schema
        for i_where in where[1:]:
            if i_where not in i_schema:
                return None
            i_schema = i_schema[i_where]
        return i_schema

    if 'default' in section:
        data = section['default']
        return data

    if '$ref' in section:
        ref = section['$ref'].split('#')
        if len(ref) > 1:
            ref_where = ref[1].split('/')
        else:
            ref_where = []

        if ref[0] == '':
            ref_section = get_section_from_fragment_path(ref_where, schema_root)
            return generate_type(root_dir, schema_root, ref_section, verbose=verbose)
        else:
            abs_file = os.path.abspath(os.path.join(root_dir, ref[0]))
            if os.path.isfile(abs_file):
                subschema = get_local_schema(abs_file, verbose=verbose)
                ref_section = get_section_from_fragment_path(ref_where, subschema)
                data = generate_type(root_dir, schema_root, ref_section, verbose=verbose)
                return data
            else:
                print('WARNING: root directory is URL or it does not exist; URL are not supported yet')
            print('WARNING: $ref non-this-document not supported yet')

    if 'enum' in section:
        data = section['enum'][0]
        return data

    if 'type' in section:
        section_type = section['type']
    else:
        section_type = 'number'

    # types from specification

    if section_type == 'string':
        data = ""

        if 'minLength' in section:
            data = 'a' * section['minLength']

        # TODO pattern
        # TODO format
    elif section_type == 'integer':
        data = 0

        if 'multipleOf' in section:
            data = section['multipleOf']

        if 'minimum' in section:
            data = section['minimum']

        if 'exclusiveMinimum' in section:
            if 'multipleOf' in section and section['multipleOf'] != 1:
                data = section['exclusiveMinimum'] + section['multipleOf']
            else:
                data = section['exclusiveMinimum'] + 1

        if 'exclusiveMinimum' is True: # draft-4
            data += 1
            # TODO check invalid combination of *minimum/*maximum/multiple
            #if 'maximum' in section and data > section['maximum']:
            #    raise Exception('')
    elif section_type == 'number':
        data = 0.0

        if 'multipleOf' in section:
            data = section['multipleOf']

        if 'minimum' in section:
            data = section['minimum']

        if 'exclusiveMinimum' in section and 'exclusiveMinimum' is not False:
            if 'exclusiveMinimum' is True: # draft-4
                exclusive_minimum = section['minimum']
            else:
                exclusive_minimum = section['exclusiveMinimum']
            m, e = math.frexp(exclusive_minimum)
            value =  (m + sys.float_info.epsilon) * 2 ** e
            if 'multipleOf' in section:
                multiple_of = section['multipleOf']
                value = math.ceil(value / multiple_of) * multiple_of

            data = value
        # TODO check invalid combination of *minimum/*maximum/multiple
    elif section_type == 'object':
        data = generate_dict(root_dir, section, verbose=verbose)
    elif section_type == 'array':
        data = [0]

        if 'minItems' in section:
            data = [0] * section['minItems']

        if 'items' in section:
            if type(section['items']) == type([]):
                data = []
                for item in section['items']:
                    data.append(generate_type(root_dir, schema_root, item, verbose=verbose))
            elif type(section['items']) == type({}):
                    data = [generate_type(root_dir, schema_root, section['items'], verbose=verbose)]
                    if 'minItems' in section:
                        data = data * section['minItems']
            else:
                print('WARNING: Unsupported array items type {type}'.format(type=type(section['items'])))
                data = ['warning_unsupported_array_items_type']
                return data


        # TODO items one
        # TODO items list
        # TODO contains
        # TODO uniqueItems
    elif section_type == 'boolean':
        data = False
    elif section_type == 'null':
        data = None
    else:
        data = ['warning_unsupported_type']
        print('WARNING: Not supported type: {section_type} in section "{section_name}"'.format(section_type=section_type, section_name=section_name))

    return data

def generate_dict(root_dir, schema_object, verbose=False):
    data = {}
    for property_name in schema_object['properties']:
        property = schema_object['properties'][property_name]
        data[property_name] = generate_type(root_dir, schema_object, property, verbose=verbose)

    return data

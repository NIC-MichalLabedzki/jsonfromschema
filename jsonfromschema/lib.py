import collections
import json
import math
import os
import sys
import pprint


def generate_type(root_dir, schema_root, section, optional_args):
    def get_local_schema(schema_file, optional_args):
        with open(schema_file, 'r') as input:
            schema = json.load(input)
            if optional_args['verbose']:
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

    if 'const' in section:
        return section['const']

    if optional_args['no-default'] == False:
        if 'default' in section:
            data = section['default']
            return data

    if optional_args['no-examples'] == False:
        if 'examples' in section:
            data = section['examples'][0]
            return data

    if 'enum' in section:
        data = section['enum'][0]
        return data

    if '$ref' in section:
        ref = section['$ref'].split('#')
        if len(ref) > 1:
            ref_where = ref[1].split('/')
        else:
            ref_where = []

        if ref[0] == '':
            ref_section = get_section_from_fragment_path(ref_where, schema_root)
            return generate_type(root_dir, schema_root, ref_section, optional_args)
        else:
            abs_file = os.path.abspath(os.path.join(root_dir, ref[0]))
            if os.path.isfile(abs_file):
                subschema = get_local_schema(abs_file, optional_args)
                ref_section = get_section_from_fragment_path(ref_where, subschema)
                data = generate_type(root_dir, schema_root, ref_section, optional_args)
                return data
            else:
                print('WARNING: root directory is URL or it does not exist; URL are not supported yet')
                return None

    if 'type' in section:
        if isinstance(section['type'], list) and len(section['type']) >= 1:
            # NOTE: use first type only is enough
            section_type = section['type'][0]
        else:
            section_type = section['type']
    else:
        # NOTE: any type is ok so use "number"
        section_type = 'number'

    if 'anyOf' in section:
        if len(section['anyOf']) < 1:
            print('WARNING: Invalid anyOf section, need at least one item')
            return None
        return generate_type(root_dir, schema_root, section['anyOf'][0], optional_args)
    if 'not' in section:
        # TODO
        print('WARNING: "not" is not supported yet')
    if 'allOf' in section:
        # TODO
        print('WARNING: "allOf" is not supported yet')
    if 'oneOf' in section:
        # TODO
        # NOTE: it does not mean "one of them", but "exactly one of them"
        # for example {int, multileOf=3}{int, multileOf=5} then int==15 is invalid because match both
        # NOTE 2: "default" field must be ignored in this case
        #
        # strategy:
        # check types: only integer and number common part
        count_typed = {}
        count_any = {'counter': 0, 'list': []}
        for item in section['oneOf']:
            detected_type = None
            if 'type' in item:
                if isinstance(item['type'], list) and len(item['type']) >= 1:
                    or_types_counter = collections.Counter(item['type'])
                    detected_type = None
                    if or_types_counter['null'] == 1:
                        detected_type = 'null'
                    elif or_types_counter['boolean'] == 1:
                        detected_type = 'boolean'
                    elif or_types_counter['string'] == 1:
                        detected_type = 'string'
                    elif or_types_counter['array'] == 1:
                        detected_type = 'array'
                    elif or_types_counter['object'] == 1:
                        detected_type = 'object'
                    else:
                        if or_types_counter['integer'] == 1 and or_types_counter['number'] == 0:
                            detected_type = 'integer'
                        if or_types_counter['number'] == 1 and or_types_counter['integer'] == 0:
                            detected_type = 'number'
                else:
                    detected_type = item['type']
            else:
                if 'const' in item:
                    if type(item['const']) is type('string'):
                        detected_type = 'string'
                    elif type(item['const']) is type(1.0):
                        detected_type = 'number'
                    elif type(item['const']) is type(1):
                        detected_type = 'integer'
                    elif type(item['const']) is type(False):
                        detected_type = 'boolean'
                    elif type(item['const']) is type(None):
                        detected_type = 'null'
                    elif type(item['const']) is type({}):
                        detected_type = 'object'
                    elif type(item['const']) is type([]):
                        detected_type = 'array'

            if detected_type is not None and detected_type not in count_typed:
                count_typed[detected_type] = {}
                count_typed[detected_type]['counter'] = 0
                count_typed[detected_type]['list'] = []

            if detected_type is not None:
                count_typed[detected_type]['counter'] += 1
                count_typed[detected_type]['list'].append(item)
            else:
                count_any['counter'] += 1
                count_any['list'].append(item)

        # const reduction
        for i_type in count_typed:
            current_const = None
            the_same_const_counter = 0
            non_const_counter =0

            for item in count_typed[i_type]['list']:
                if 'const' not in item:
                    non_const_counter += 1
                    continue
                if current_const == None:
                    current_const = item
                    continue
                else:
                    if current_const['const'] == item['const']:
                        the_same_const_counter += 1

            if non_const_counter == 0 and the_same_const_counter == 0:
                count_typed[i_type]['counter'] = 1
                count_typed[i_type]['list'] = [current_const]

        # last choice
        if count_any['counter'] == 0:
            for i_type in count_typed:
                if count_typed[i_type]['counter'] == 1 and (i_type == 'null' or i_type == 'boolean' or i_type == 'string' or i_type == 'array' or i_type == 'object'):
                    return generate_type(root_dir, schema_root, count_typed[i_type]['list'][0], optional_args)
                if i_type == 'number' and 'integer' not in count_typed and count_typed[i_type]['counter'] == 1:
                    return generate_type(root_dir, schema_root, count_typed[i_type]['list'][0], optional_args)
                if i_type == 'integer' and 'number' not in count_typed and count_typed[i_type]['counter'] == 1:
                    return generate_type(root_dir, schema_root, count_typed[i_type]['list'][0], optional_args)

        print('TYPED', count_typed)
        print('WARNING: complex "oneOf" is not supported yet')

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
        data = generate_dict(root_dir, section, optional_args)
    elif section_type == 'array':
        data = [0]

        if 'minItems' in section:
            data = [0] * section['minItems']

        if 'items' in section:
            if type(section['items']) == type([]):
                data = []
                for item in section['items']:
                    data.append(generate_type(root_dir, schema_root, item, optional_args))
            elif type(section['items']) == type({}):
                    data = [generate_type(root_dir, schema_root, section['items'], optional_args)]
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
        print('WARNING: Not supported type: {section_type}'.format(section_type=section_type))

    return data


def generate_dict(root_dir, schema_object, optional_args=None):
    def set_default(dict, key, value):
        if key not in dict:
            dict[key] = value
    if optional_args == None:
        optional_args = {}

    set_default(optional_args, 'verbose', False)
    set_default(optional_args, 'no-default', False)
    set_default(optional_args, 'no-examples', False)

    data = {}
    for property_name in schema_object['properties']:
        property = schema_object['properties'][property_name]
        data[property_name] = generate_type(root_dir, schema_object, property, optional_args)

    return data


def generate_dict_from_file(schema_file, optional_args):
    root_file = os.path.abspath(schema_file)
    root_dir = os.path.dirname(root_file)

    with open(root_file, 'r') as input:
        schema = json.load(input)
        if optional_args['verbose']:
            print('>>> Schema is:')
            pprint.pprint(schema)
    input.close()

    data = generate_dict(root_dir, schema, optional_args)
    return data


def generate_dict_from_package(package, path, optional_args):
    import pkg_resources

    schema_text = pkg_resources.resource_string(package, path)
    schema = json.load(schema_text)
    data = generate_dict(package, schema, optional_args, from_pkg_resources=True)
    return data

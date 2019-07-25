import collections
import json
import math
import os
import sys
import pprint


def get_subschema_from_fragment_path(where, schema, is_output=False):
    i_schema = schema
    if is_output:
        where_set = where
    else:
        where_set = where[1:]

    for i_where in where_set:
        if is_output and i_where == 'properties':
            continue
        if i_where not in i_schema:
            if type(i_schema) == type([]) and i_where.isdigit() and i_schema[int(i_where)] != None:
                i_schema = i_schema[int(i_where)]
                continue
            return None
        i_schema = i_schema[i_where]
    return i_schema

def generate_value(output_dict, output_json_pointer, root, schema_root, section, optional_args):
    def get_local_schema(schema_file, optional_args):
        with open(schema_file, 'r') as input:
            schema = json.load(input)
            if optional_args['verbose']:
                print('>>> Schema[{}] is:'.format(schema_file))
                pprint.pprint(schema)
        return schema

    def json_pointer_up(json_pointer):
        path = output_json_pointer.split('/')[:-1]
        return '/' + '/'.join(path)

    def save_data(output_dict, output_json_pointer, value):
        path = output_json_pointer.split('/')
        i_output_dict = output_dict

        if len(path) >= 2 and path[1] != '':
            for i_path in path[:-1]:
                if type(i_output_dict) == type([]) and i_path.isdigit():
                    index_path = int(i_path)
                    if len(i_output_dict) - 1 < index_path:
                        i_output_dict.insert(index_path, {})
                else:
                    index_path = i_path
                    if index_path not in i_output_dict:
                        i_output_dict[index_path] = {}

                i_output_dict = i_output_dict[index_path]

        if type(i_output_dict) == type([]):
            i_output_dict.insert(int(path[-1]), value)
        else:
            i_output_dict[path[-1]] = value


    if 'const' in section:
        data = section['const']
        save_data(output_dict, output_json_pointer, data)
        return

    if optional_args['no-default'] == False:
        if 'default' in section:
            data = section['default']
            save_data(output_dict, output_json_pointer, data)
            return

    if optional_args['no-examples'] == False:
        if 'examples' in section:
            data = section['examples'][0]
            save_data(output_dict, output_json_pointer, data)
            return

    if 'enum' in section:
        data = section['enum'][0]
        save_data(output_dict, output_json_pointer, data)
        return

    if '$ref' in section:
        ref = section['$ref'].split('#')
        if len(ref) > 1:
            ref_where = ref[1].split('/')
        else:
            ref_where = []

        if ref[0] == '':
            ref_section = get_subschema_from_fragment_path(ref_where, schema_root)
            generate_value(output_dict, output_json_pointer, root, schema_root, ref_section, optional_args)
            return
        else:
            if optional_args['pkg_resource_root'] is not None:
                import pkg_resources
                path = '/'.join(optional_args['pkg_resource_root'].split('/')[0:-1]) + '/' + ref[0]

#                xpath = path.split('/')
#                for i_path, item in enumerate(xpath):
#                    if xpath[i_path] == '.':
#                        del xpath[i_path]
#                    if xpath[i_path] == '..':
#                        del xpath[i_path]
#                        del xpath[i_path - 1]
#                path = '/'.join(xpath)

                old_path = optional_args['pkg_resource_root']
                optional_args['pkg_resource_root'] = path
                subschema_text = pkg_resources.resource_string(root, path).decode('utf-8')
                subschema = json.loads(subschema_text)
                if optional_args['verbose']:
                    print('>>> Schema[{} in {}] is:'.format(path, root))
                    pprint.pprint(subschema)

                ref_section = get_subschema_from_fragment_path(ref_where, subschema)
                generate_value(output_dict, output_json_pointer, root, schema_root, ref_section, optional_args)
                optional_args['pkg_resource_root'] = old_path
                return
            else:
                abs_file = os.path.abspath(os.path.join(root, ref[0]))
                ref_root = os.path.dirname(abs_file)
                if os.path.isfile(abs_file):
                    subschema = get_local_schema(abs_file, optional_args)
                    ref_section = get_subschema_from_fragment_path(ref_where, subschema)
                    generate_value(output_dict, output_json_pointer, ref_root, schema_root, ref_section, optional_args)
                    return
                else:
                    print('WARNING: root directory is URL or it does not exist; URL are not supported yet')
                    return

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
            return
        generate_value(output_dict, output_json_pointer, root, schema_root, section['anyOf'][0], optional_args)
        return
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
                    if type(item['const']) is type('string') or type(item['const']) is type(u'unicode_string_for_python2'):
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
            if optional_args['maximum'] == False:
                for i_type in count_typed:
                    if count_typed[i_type]['counter'] == 1 and i_type == 'null':
                        generate_value(output_dict, output_json_pointer, root, schema_root, count_typed[i_type]['list'][0], optional_args)
                        return

            # TODO: better --maximum, try object, then array, string, number, boolean, null

            for i_type in count_typed:
                if count_typed[i_type]['counter'] == 1 and (i_type == 'null' or i_type == 'boolean' or i_type == 'string' or i_type == 'array' or i_type == 'object'):
                    generate_value(output_dict, output_json_pointer, root, schema_root, count_typed[i_type]['list'][0], optional_args)
                    return
                if i_type == 'number' and 'integer' not in count_typed and count_typed[i_type]['counter'] == 1:
                    generate_value(output_dict, output_json_pointer, root, schema_root, count_typed[i_type]['list'][0], optional_args)
                    return
                if i_type == 'integer' and 'number' not in count_typed and count_typed[i_type]['counter'] == 1:
                    generate_value(output_dict, output_json_pointer, root, schema_root, count_typed[i_type]['list'][0], optional_args)
                    return

        # NOTE: there is 'anyType' found but I believe it does not match null or boolean, because they are trivial and are value as keywords
        for i_type in ['null', 'boolean']:
            if count_typed[i_type]['counter'] == 1:
                generate_value(output_dict, output_json_pointer, root, schema_root, count_typed[i_type]['list'][0], optional_args)
                return

        print('TYPED', count_typed)
        print('TYPED any', count_any['counter'])
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
        if optional_args['maximum'] == True:
            properties_list = section['properties']
        else:
            if 'required' in section:
                properties_list = section['required']
            else:
                properties_list = []

        for property_name in properties_list:
            property = section['properties'][property_name]
            if output_json_pointer != '/':
                new_output_json_pointer = output_json_pointer + '/' + property_name
            else:
                new_output_json_pointer = output_json_pointer + property_name

            generate_value(output_dict, new_output_json_pointer, root, section, property, optional_args)

        if properties_list == []:
            data = {}
            save_data(output_dict, output_json_pointer, data)

        if 'if' in section:
            if 'then' not in section and 'else' not in section:
                print('WARNING: Invalid if-then-else properties in schema: there is no "then" and "else"')
                return

            property = section['if']
            if_section = section # TODO: output_dict

            json_pointer = '' + output_json_pointer
            while 'const' not in property:
                key = list(property.keys())[0]
                property = property[key]
                if_section = if_section[key]
                if json_pointer == '/':
                    json_pointer += key
                else:
                    json_pointer += '/' + key
            if 'const' in property:
                if_output_value = get_subschema_from_fragment_path(json_pointer.split('/'), output_dict, True)

                if if_output_value is None:
                    return

                if if_output_value == property['const']:
                    # TODO: properties may not exist and it may be not object
                    for prop in section['then']['properties']:
                        if output_json_pointer != '/':
                            new_output_json_pointer = output_json_pointer + '/' + prop
                        else:
                            new_output_json_pointer = output_json_pointer + prop

                        generate_value(output_dict, new_output_json_pointer, root, section, section['then']['properties'][prop], optional_args)
                else:
                    # TODO: properties may not exist and it may be not object
                    for prop in section['else']['properties']:
                        if output_json_pointer != '/':
                            new_output_json_pointer = output_json_pointer + '/' + prop
                        else:
                            new_output_json_pointer = output_json_pointer + prop

                        generate_value(output_dict, new_output_json_pointer, root, section, section['else']['properties'][prop], optional_args)

        # TODO: process if-them-else
        # TODO: process patternProperties
        # TODO: minProperties
        # TODO: maxProperties
        # TODO: propertyNames {pattern: ""}
        # TODO: dependencies
        # TODO: additionalProperties for invalid schema generation
        return
    elif section_type == 'array':
        data = [0]

        min_items = 0
        if 'minItems' in section:
            min_items = section['minItems']
            data = [0] * section['minItems']

            save_data(output_dict, output_json_pointer, [])

        if 'items' in section:
            if type(section['items']) == type([]):
                i_items = 0
                for _ in range(min_items):
                    for item in section['items']:
                        if i_items > min_items:
                            break
                        if output_json_pointer == '/':
                            new_output_json_pointer = output_json_pointer + str(i_items)
                        else:
                            new_output_json_pointer = output_json_pointer + '/' + str(i_items)
                        generate_value(output_dict, new_output_json_pointer, root, schema_root, item, optional_args)
                        i_items += 1
                if min_items == 0:
                    data = []
                else:
                    return
            elif type(section['items']) == type({}):
                i_items = 0
                for _ in range(min_items):
                    if output_json_pointer == '/':
                        new_output_json_pointer = output_json_pointer + str(i_items)
                    else:
                        new_output_json_pointer = output_json_pointer + '/' + str(i_items)
                    generate_value(output_dict, new_output_json_pointer, root, schema_root, section['items'], optional_args)
                    i_items += 1
                if min_items == 0:
                    data = []
                else:
                    return
            else:
                print('WARNING: Unsupported array items type {type}'.format(type=type(section['items'])))
                data = ['warning_unsupported_array_items_type']
                save_data(output_dict, output_json_pointer, data)
                return


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

    save_data(output_dict, output_json_pointer, data)

    return


def generate_dict(root_name, schema_dict, optional_args=None):
    def set_default(dict, key, value):
        if key not in dict:
            dict[key] = value
    if optional_args == None:
        optional_args = {}

    set_default(optional_args, 'verbose', False)
    set_default(optional_args, 'no-default', False)
    set_default(optional_args, 'no-examples', False)
    set_default(optional_args, 'maximum', False)
    set_default(optional_args, 'pkg_resource_root', None)
    set_default(optional_args, 'subschema', None)

    if optional_args['subschema'] is None:
        subschema_dict = schema_dict
    else:
        subschema_path = optional_args['subschema'].split('/')
        subschema_dict = get_subschema_from_fragment_path(subschema_path, schema_dict)

    output_dict = {}
    output_json_pointer = '/'
    generate_value(output_dict, output_json_pointer, root_name, schema_dict, subschema_dict, optional_args)
    return output_dict['']


def generate_dict_from_text(root_name, schema_text, optional_args=None):
    schema_dict = json.loads(schema_text)

    data = generate_dict(root_name, schema_dict, optional_args)

    return data


def generate_dict_from_file(schema_file, optional_args=None):
    root_file = os.path.abspath(schema_file)
    root_dir = os.path.dirname(root_file)

    with open(root_file, 'r') as input:
        schema = json.load(input)
        if optional_args is not None and optional_args['verbose']:
            print('>>> Schema is:')
            pprint.pprint(schema)
    input.close()

    data = generate_dict(root_dir, schema, optional_args)
    return data


def generate_dict_from_package(package, path, optional_args=None):
    import pkg_resources

    def set_default(dict, key, value):
        if key not in dict:
            dict[key] = value
    if optional_args == None:
        optional_args = {}

    set_default(optional_args, 'verbose', False)
    set_default(optional_args, 'pkg_resource_root', path)

    schema_text = pkg_resources.resource_string(package, path).decode('utf-8')

    schema = json.loads(schema_text)

    if optional_args['verbose']:
        print('>>> Schema is:')
        pprint.pprint(schema)

    data = generate_dict(package, schema, optional_args)
    return data

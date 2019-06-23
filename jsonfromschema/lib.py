import math
import sys


def generate_type(section):
    print('generate_type', section)

    section_type = section['type']

    if 'default' in section:
        data = section['default']
        return data

    if 'enum' in section:
        data = section['enum'][0]
        return data

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
        data = generate_dict(section)
    elif section_type == 'array':
        data = [0]

        if 'minItems' in section:
            data = [0] * section['minItems']

        if 'items' in section:
            if type(section['items']) == type([]):
                data = []
                for item in section['items']:
                    data.append(generate_type(item))
            elif type(section['items']) == type({}):
                    data = [generate_type(section['items'])]
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

def generate_dict(schema_object):
    data = {}
    for property_name in schema_object['properties']:
        property = schema_object['properties'][property_name]
        data[property_name] = generate_type(property)

    return data

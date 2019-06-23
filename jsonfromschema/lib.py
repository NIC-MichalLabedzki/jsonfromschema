import math
import sys


def generate_dict(schema_object):
    data = {}
    for property_name in schema_object['properties']:
        property = schema_object['properties'][property_name]
        property_type = property['type']

        if 'default' in property:
            data[property_name] = property['default']
            continue
        
        if 'enum' in property:
            data[property_name] = property['enum'][0]
            continue

        if property_type == 'string':
            data[property_name] = ""

            if 'minLength' in property:
                data[property_name] = 'a' * property['minLength']

            # TODO pattern
            # TODO format
        elif property_type == 'integer':
            data[property_name] = 0

            if 'multipleOf' in property:
                data[property_name] = property['multipleOf']
            
            if 'minimum' in property:
                data[property_name] = property['minimum']
            
            if 'exclusiveMinimum' in property:
                data[property_name] = property['exclusiveMinimum'] + 1
            
            if 'exclusiveMinimum' is True: # draft-4
                data[property_name] += 1
                # TODO check invalid combination of *minimum/*maximum/multiple
                #if 'maximum' in property and data[property_name] > property['maximum']:
                #    raise Exception('')
        elif property_type == 'number':
            data[property_name] = 0.0
    
            if 'multipleOf' in property:
                data[property_name] = property['multipleOf']

            if 'minimum' in property:
                data[property_name] = property['minimum']
            
            if 'exclusiveMinimum' in property and 'exclusiveMinimum' is not False:
                if 'exclusiveMinimum' is True: # draft-4
                    exclusive_minimum = property['minimum']
                else:
                    exclusive_minimum = property['exclusiveMinimum']
                m, e = math.frexp(exclusive_minimum)
                value =  (m + sys.float_info.epsilon) * 2 ** e
                if 'multipleOf' in property:
                    multiple_of = property['multipleOf']
                    value = math.ceil(value / multiple_of) * multiple_of
                
                data[property_name] = value   
            # TODO check invalid combination of *minimum/*maximum/multiple
        elif property_type == 'object':
            data[property_name] = generate_dict(property)
        elif property_type == 'array':
            data[property_name] = [0]
            # TODO items one
            # TODO items list
            # TODO contains
            # TODO minItems
            # TODO uniqueItems
        elif property_type == 'boolean':
            data[property_name] = False
        elif property_type == 'null':
            data[property_name] = None
        else:
            data[property_name] = ['warning_unsupported_type']
            print('WARNING: Not supported type: {property_type} in property "{property_name}"'.format(property_type=property_type, property_name=property_name))

    return data

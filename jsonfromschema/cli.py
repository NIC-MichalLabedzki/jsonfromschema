import argparse
import json
import os
import pprint
import sys
import jsonfromschema.lib




def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Generate JSON data file (*.json) from JSON Schema')
    parser.add_argument('schema', type=str, help='path to JSON Schema file or python packages resource [--from-python-package]')
    parser.add_argument('output', type=str, help='path to JSON data output file')
    parser.add_argument('-v', '--verbose', action="store_true", help='verbose mode')
    parser.add_argument('-w', '--validate', action="store_true", help='use jsonschema to validate output')
    parser.add_argument('--no-default', action="store_true", help='do not use \'default\' fields in jsonschema')
    parser.add_argument('--no-examples', action="store_true", help='do not use \'default\' fields in jsonschema')
    parser.add_argument('--from-python-package', type=str, help='\'schema\' is path to python package resource')
    args = parser.parse_args()

    optional_args = { 'verbose': False}

    if args.no_default:
        optional_args['no-default'] = True
    if args.no_examples:
        optional_args['no-examples'] = True
    if args.verbose:
        optional_args['verbose'] = True

    # early check if we can save results, before processing
    with open(args.output, 'w') as output:
        pass

    if not args.from_python_package:
        with open(args.schema, 'r') as input:
            schema = json.load(input)
            if args.verbose:
                print('>>> Schema is:')
                pprint.pprint(schema)

        root_file = os.path.abspath(args.schema)
        root_dir = os.path.dirname(root_file)

        output_dict = jsonfromschema.lib.generate_dict(root_dir, schema, optional_args)
    else:
        output_dict = jsonfromschema.lib.generate_dict_from_package(args.from_python_package, args.schema, optional_args)


    with open(args.output, 'w') as output:
        if args.verbose:
            print('>>> Output is:')
            pprint.pprint(output_dict)
        output_json = json.dumps(output_dict)
        output.write(output_json)

    if args.validate:
        if args.from_python_package:
            print('WARNING: Sorry, \'jsonschema\' is used for validation, but it does not support validating from python package resources')
            return
        import pkgutil
        if not pkgutil.find_loader("jsonschema"):
            print('ERROR: jsonschema not installed, do: pip install jsonschema --user')
            sys.exit(1)
        import jsonschema  # optional dependancy

        resolver = jsonschema.RefResolver(base_uri='file:{}'.format(root_file), referrer=schema)
        jsonschema.validate(instance=output_dict, schema=schema, resolver=resolver)
        if args.verbose:
            print('>>> Validation result: OK')
    sys.exit(0)

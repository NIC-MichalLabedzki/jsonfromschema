import argparse
import json
import os
import pprint
import sys
import jsonfromschema.lib


def main(args=sys.argv[1:]):
    import select
    if select.select([sys.stdin,],[],[],0.0)[0]:
        has_stdin_data = True
    else:
        has_stdin_data = False

    parser = argparse.ArgumentParser(description='Generate JSON data file (*.json) from JSON Schema')
    if not has_stdin_data:
        parser.add_argument('schema', type=str, help='path to JSON Schema file or python packages resource [--from-python-package]')
        parser.add_argument('output', type=str, help='path to JSON data output file')
    parser.add_argument('-v', '--verbose', action="store_true", help='verbose mode')
    parser.add_argument('-w', '--validate', action="store_true", help='use jsonschema to validate output')
    parser.add_argument('--no-default', action="store_true", help='do not use \'default\' fields in jsonschema')
    parser.add_argument('--no-examples', action="store_true", help='do not use \'default\' fields in jsonschema')
    parser.add_argument('--maximum', action="store_true", help='generate as complex json as possible (by implementation); for example ignore "required" and favor "object" over less complicated fields')
    if not has_stdin_data:
        parser.add_argument('--from-python-package', type=str, help='\'schema\' is path to python package resource, this option needs package name as argument')
    args = parser.parse_args()

    optional_args = { 'verbose': False}

    if args.no_default:
        optional_args['no-default'] = True
    if args.no_examples:
        optional_args['no-examples'] = True
    if args.verbose:
        optional_args['verbose'] = True
    if args.maximum:
        optional_args['maximum'] = True

    if has_stdin_data:
        output_fp = sys.stdout
    else:
        # early check if we can save results, before processing
        output_fp = open(args.output, 'w')

    if has_stdin_data:
        schema_text = sys.stdin.read()
        schema = json.loads(schema_text)

        output_dict = jsonfromschema.lib.generate_dict_from_text('', schema_text, optional_args)
        root_file = ''
    else:
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


    if args.verbose:
        print('>>> Output is:')
        pprint.pprint(output_dict)
    output_json = json.dumps(output_dict)
    output_fp.write(output_json)
    if output_fp != sys.stdout:
        output_fp.close()

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

import argparse
import json
import sys
import jsonfromschema.lib

from pprint import pprint


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Generate JSON data file (*.json) from JSON Schema')
    parser.add_argument('schema', type=str, help='path to JSON Schema file')
    parser.add_argument('output', type=str, help='path to JSON data output file')
    parser.add_argument('-v', '--verbose', action="store_true", help='verbose mode')
    args = parser.parse_args()
    print('schema', args.schema)
    print('output', args.output)

    with open(args.schema, 'r') as input:
        schema = json.load(input)
        if args.verbose:
            print('>>> Schema is:')
            pprint(schema)
    input.close()

    with open(args.output, 'w') as output:
        output_dict = jsonfromschema.lib.generate_dict(schema)
        if args.verbose:
            print('>>> Output is:')
            pprint(output_dict)
        output_json = json.dumps(output_dict)
        output.write(output_json)
    output.close()
    
    sys.exit(0) 

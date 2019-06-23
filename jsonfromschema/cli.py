import argparse
import sys

def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Generate JSON data file (*.json) from JSON Schema')
    parser.add_argument('schema', type=str, help='path to JSON Schema file')
    parser.add_argument('output', type=str, help='path to JSON data output file')
    args = parser.parse_args()
    sys.exit(0) 

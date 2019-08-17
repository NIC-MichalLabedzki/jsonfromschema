import json

#def test_main_cli():
    #pass
    #import jsonfromschema.cli
    #jsonfromschema.cli.main()

def expected_test_results(test_file, suffix=''):
    if suffix:
        suffix = '.' + suffix
    file = test_file + suffix + '.results.json'
    results = {}
    with open(file) as f:
        results = json.load(f)
    return results

def test_main():
    import jsonfromschema.lib

    test = 'tests/test_schema_main.json'

    expected_results = expected_test_results(test)
    our_results = jsonfromschema.lib.generate_dict_from_file(test)

    assert our_results == expected_results

def test_main_maximum():
    import jsonfromschema.lib

    test = 'tests/test_schema_main.json'

    expected_results = expected_test_results(test, 'maximum')
    our_results = jsonfromschema.lib.generate_dict_from_file(test, {'maximum': True})

    assert our_results == expected_results


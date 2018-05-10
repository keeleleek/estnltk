from estnltk.core import rel_path
from estnltk.taggers import TaggerTester
from estnltk.taggers import AddressGrammarTagger

# test data created by estnltk/dev_documentation/testing/create_tests_for_address_taggers.ipynb


def test_tagger():
    tagger = AddressGrammarTagger()
    input_file = rel_path('tests/test_taggers/test_standard_taggers/address_grammar_tagger_input.json')
    target_file = rel_path('tests/test_taggers/test_standard_taggers/address_grammar_tagger_target.json')

    tester = TaggerTester(tagger, input_file, target_file)
    tester.load()
    tester.run_tests()

from typing import Sequence

from estnltk.taggers import RegexTaggerOld
from estnltk.taggers.tagger_new import TaggerNew

from .robust_date_number_vocabulary import vocabulary as voc


class RobustDateNumberTagger(TaggerNew):
    """
    Tags dates and numbers.
    """
    conf_param = ['tagger']

    def __init__(self,
                 output_attributes: Sequence=('grammar_symbol', 'regex_type', 'value'),
                 conflict_resolving_strategy: str='MAX',
                 overlapped: bool=True,
                 output_layer: str='dates_numbers',
                 ):
        self.output_attributes = output_attributes
        self.output_layer = output_layer
        self.input_layers = []
        self.tagger = RegexTaggerOld(vocabulary=voc,
                                     attributes=output_attributes,
                                     conflict_resolving_strategy=conflict_resolving_strategy,
                                     priority_attribute='_priority_',
                                     overlapped=overlapped,
                                     layer_name=output_layer)

    def make_layer(self, raw_text, layers, status):
        return self.tagger.make_layer(raw_text, layers, status)

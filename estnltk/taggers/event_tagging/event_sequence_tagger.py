from estnltk.taggers import TaggerOld
from estnltk.text import Layer
from estnltk.layer_operations import resolve_conflicts
from collections import defaultdict

class EventSequenceTaggerOld(TaggerOld):
    """
    Tags event sequences on a given layer. Creates an enveloping layer.
    """
    description = 'Tags event sequences.'
    layer_name = None
    attributes = ('match',)
    depends_on = None
    configuration = None

    def __init__(self,
                 layer_name,
                 input_layer_name,
                 input_attribute,
                 episodes,
                 conflict_resolving_strategy='MAX',
                 ):
        """Initialize a new EventSequenceTaggerOld instance.

        Parameters
        ----------
        layer_name: str
            The name of the new layer.
        input_layer_name: str
            The name of the input layer.
        input_attribute: str
            The name of the input layer attribute.
        episodes: list of tuples
            input layer attribute value tuples to annotate
        conflict_resolving_strategy: 'ALL', 'MAX', 'MIN' (default: 'MAX')
            Strategy to choose between overlapping events.
        """

        if conflict_resolving_strategy not in ['ALL', 'MIN', 'MAX']:
            raise ValueError("Unknown conflict_resolving_strategy '%s'." % conflict_resolving_strategy)
        self._conflict_resolving_strategy = conflict_resolving_strategy
        self.layer_name = layer_name
        self._input_layer_name = input_layer_name
        self._input_attribute = input_attribute
        
        self.depends_on = [input_layer_name]
        self.configuration = {}
        self.configuration['input_layer_name'] = input_layer_name
        self.configuration['input_attribute'] = input_attribute
        self.configuration['episodes'] = str(len(episodes)) + ' episodes'
        self.configuration['conflict_resolving_strategy'] = conflict_resolving_strategy
        
        self.heads = defaultdict(list)
        for episode in episodes:
            self.heads[episode[0]].append(episode[1:])


    def tag(self, text, return_layer=False):
        input_layer = text[self._input_layer_name]
        layer = Layer(
                      name=self.layer_name,
                      attributes = self.attributes,
                      enveloping=self._input_layer_name,
                      ambiguous=False)
        heads = self.heads
        value_list = getattr(input_layer, self._input_attribute)
        if input_layer.ambiguous:
            for i, values in enumerate(value_list):
                for value in set(values):
                    if value in heads:
                        for tail in heads[value]:
                            if i + len(tail) < len(value_list):
                                match = True
                                for a, b in zip(tail, value_list[i+1:i+len(tail)+1]):
                                    if a not in b:
                                        match = False
                                        break
                                if match:
                                    span = input_layer.spans[i:i+len(tail)+1]
                                    span.match = (value,)+tail
                                    layer.add_span(span)
        else:
            for i, value in enumerate(value_list):
                if value in heads:
                    for tail in heads[value]:
                        if i + len(tail) < len(value_list):
                            match = True
                            for a, b in zip(tail, value_list[i+1:i+len(tail)+1]):
                                if a != b:
                                    match = False
                                    break
                            if match:
                                span = input_layer.spans[i:i+len(tail)+1]
                                span.match = (value,)+tail
                                layer.add_span(span)

        resolve_conflicts(layer, conflict_resolving_strategy=self._conflict_resolving_strategy)

        if return_layer:
            return layer
        text[self.layer_name] = layer
        return text

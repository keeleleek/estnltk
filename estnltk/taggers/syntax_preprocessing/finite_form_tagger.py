from estnltk.taggers import TaggerOld
from estnltk.taggers import VabamorfTaggerOld
from estnltk.rewriting import MorphToSyntaxMorphRewriter
from estnltk.rewriting import FiniteFormRewriter



class FiniteFormTaggerOld(TaggerOld):
    description = 'Tags finite form tags for verbs.'
    layer_name = 'finite_form'
    attributes = VabamorfTaggerOld.attributes + ('fin',)
    depends_on = ['morph_analysis']
    configuration = {}

    def __init__(self, fs_to_synt_rules_file):
        self.morph_to_syntax_morph_rewriter = MorphToSyntaxMorphRewriter(fs_to_synt_rules_file)
        self.finite_form_rewriter = FiniteFormRewriter()

    def tag(self, text, return_layer=False):
        new_layer = text['morph_analysis']
        source_attributes = new_layer.attributes
        target_attributes = source_attributes
        new_layer = new_layer.rewrite(
            source_attributes = source_attributes,
            target_attributes = target_attributes,
            rules = self.morph_to_syntax_morph_rewriter,
            name = 'morph_analysis',
            ambiguous = True
            )

        source_attributes = new_layer.attributes
        target_attributes = self.attributes
        new_layer = new_layer.rewrite(
            source_attributes = source_attributes,
            target_attributes = target_attributes,
            rules = self.finite_form_rewriter,
            name = self.layer_name,
            ambiguous = True
            )
        if return_layer:
            return new_layer
        text[self.layer_name] = new_layer

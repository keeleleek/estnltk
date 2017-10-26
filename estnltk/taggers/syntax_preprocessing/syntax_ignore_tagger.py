from estnltk.taggers import Tagger
from estnltk.taggers import RegexTagger

from estnltk.text import Span, SpanList, Layer

import regex as re

# ===================================================================
#   Patterns for capturing text snippets that should be ignored;
#
#   Note: these patterns are based on the patterns defined in:
#      * https://github.com/kristiinavaik/ettenten-eeltootlus
#      * https://github.com/EstSyntax/preprocessing-module
#
# ===================================================================

_lc_letter      = 'a-zöäüõžš'
_uc_letter      = 'A-ZÖÄÜÕŽŠ'
_titlecase_word = '['+_uc_letter+']['+_lc_letter+']+'
_hyphen_pat     = '(-|\u2212|\uFF0D|\u02D7|\uFE63|\u002D|\u2010|\u2011|\u2012|\u2013|\u2014|\u2015|-)'
_start_quotes   = '"\u00AB\u02EE\u030B\u201C\u201D\u201E'
_three_lc_words = '['+_lc_letter+']+\s['+_lc_letter+']+\s['+_lc_letter+']+'
_clock_time     = '((0|\D)[0-9]|[12][0-9]|2[0123])\s?:\s?([0-5][0-9])'

ignore_patterns = [ 
      # Partly based on PATT_BRACS from https://github.com/EstSyntax/preprocessing-module (aja)
      { 'comment': 'Captures sequences of 1-3 symbols in parenthesis;',
        'example': 'Tal on kaks tütart - Beatrice ( 9 ) ja Eugenie ( 8 ).',
        'type'   : 'parenthesis_1to3',
        '_priority_': (0, 0, 1, 1),
        '_regex_pattern_': re.compile(\
            r'''
            (\(\s                                                          # starts with '('
              (                                                            #
                (['''+_uc_letter+_lc_letter+'''0-9,-<>\[\]\/]{1,3}|\+)     # 1-3 symbols or +
              )                                                            #
              (                                                            #
                 \s(['''+_uc_letter+_lc_letter+'''0-9,-<>\[\]\/]{1,3}|\+)  # 1-3 symbols or +
              )*                                                           #
            \s\))                                                          # ends with ')'
            ''', re.X),
        '_group_': 1 },\
      # Note: in the previous pattern, a space is intentionally added after '(' and before ')' 
      #       in order to prevent extraction of optional word endings/prefixes, such as:
      #           ... sellest tulenevalt raamatukogu[(de)] võimalikkus ...
      #           ... Romaanilikkust [(re)]presenteerib Itaalia ...
      { 'comment': 'Captures at least 2 char sequences of 1-3 symbols in parenthesis;',
        'example': '(x 1 , x 2 , ... , K , ... , x n)',
        'type'   : 'parenthesis_1to3',
        '_priority_': (0, 0, 1, 2),
        '_regex_pattern_': re.compile(\
            r'''
            (\(                                                            # starts with '('
              (                                                            #
                (['''+_uc_letter+_lc_letter+'''0-9,.-<>\[\]\/]{1,3}|\+)    # 1-3 symbols or +
              )                                                            #
              (                                                            #
                 \s(['''+_uc_letter+_lc_letter+'''0-9,.-<>\[\]\/]{1,3}|\+) # 1-3 symbols or +
              )+                                                           #
            \))                                                            # ends with ')'
            ''', re.X),
        '_group_': 1 },\
      { 'comment': 'Captures sequences of 1-4 non-letters in parenthesis;',
        'example': 'Pariisi (1919) ja Tartu (1920) rahukonverentsid',
        'type'   : 'parenthesis_1to4',
        '_priority_': (0, 0, 1, 3),
        '_regex_pattern_': re.compile(\
            r'''
            (\(                                               # starts with '('
              (                                               #
                ([0-9,.-<>\[\]\/]{1,4}|\+)                    # 1-4 non-letters or +
              )                                               #
              (                                               #
                 \s([0-9,.-<>\[\]\/]{1,4}|\+)                 # 1-4 non-letters or +
              )*                                              #
            \))                                               # ends with ')'
            ''', re.X),
        '_group_': 1 },\
      { 'comment': 'Captures sequences of 1-4 non-letters in parenthesis;',
        'example': 'Pariis ( 1919 ) ja Tartu ( 1920 )',
        'type'   : 'parenthesis_1to4',
        '_priority_': (0, 0, 1, 4),
        '_regex_pattern_': re.compile(\
            r'''
            (\(\s*                                            # starts with '('
              (                                               #
                ([0-9,.-<>\[\]\/]{4}|\+)                      # 4 non-letters or +
              )                                               #
              (                                               #
                 \s([0-9,.-<>\[\]\/]{1,4}|\+)                 # 1-4 non-letters or +
              )*                                              #
            \s*\))                                            # ends with ')'
            ''', re.X),
        '_group_': 1 },\

      # Partly based on PATT_55 from https://github.com/EstSyntax/preprocessing-module (aja)
      { 'comment': 'Captures 1-2 comma-separated titlecase words inside parenthesis;',
        'example': '( Jaapan , Subaru )',
        'type'   : 'parenthesis_title_words',
        '_priority_': (0, 0, 2, 1),
        '_regex_pattern_': re.compile(\
            r'''
            (['''+_uc_letter+_lc_letter+'''0-9]+\s)          # preceding word
            (\(\s*                                           # starts with '('
                ('''+_titlecase_word+''')                    # titlecase word 
                (-'''+_titlecase_word+''')?                  # hyphen + titlecase word (optional)
                \s?                                          # space
                (,'''+_titlecase_word+'''\s)?                # comma + titlecase word 
            \s*\))                                           # ends with ')'
            ''', re.X),
        '_group_': 2 },\
        
      # Partly based on PATT_72 from https://github.com/EstSyntax/preprocessing-module (aja)
      { 'comment': 'Captures 2 (space-separated) titlecase words inside parenthesis;',
        'example': '( Tallinna Wado )',
        'type'   : 'parenthesis_title_words',
        '_priority_': (0, 0, 2, 2),
        '_regex_pattern_': re.compile(\
            r'''
            (\(\s*                                     # starts with '('
                ('''+_titlecase_word+''')              # titlecase word 
                (-'''+_titlecase_word+''')?            # hyphen + titlecase word (optional)
                \s+                                    # space
                ('''+_titlecase_word+''')              # titlecase word
                (-'''+_titlecase_word+''')?            # hyphen + titlecase word (optional)
            \s*\))                                     # ends with ')'
            ''', re.X),
        '_group_': 1 },\

      # Partly based on PATT_62 from https://github.com/EstSyntax/preprocessing-module (aja)
      { 'comment': 'Captures ordinal number inside parenthesis, maybe accompanied by a word;',
        'example': '( 3. koht ) või ( WTA 210. )',
        'type'   : 'parenthesis_ordinal_numbers',
        '_priority_': (0, 0, 2, 3),
        '_regex_pattern_': re.compile(\
            r'''
            (['''+_uc_letter+_lc_letter+'''0-9]+\s)    # preceding word
            (\(\s*                                     # starts with '('
                (\d+\s?\.                              # ordinal number 
                  (\s['''+_lc_letter+''']+)?|          #   followed by lc word, or 
                 '''+_uc_letter+'''+                   # uc word
                  \s\d+\s?\.)                          #   followed by ordinal number 
            \s*\))                                     # ends with ')'
            ''', re.X),
        '_group_': 2 },\

      # Partly based on PATT_45 from https://github.com/EstSyntax/preprocessing-module (tea)
      #          and on PATT_80 from https://github.com/kristiinavaik/ettenten-eeltootlus 
      { 'comment': 'Captures content inside square brackets #1 (numeric references);',
        'example': 'Nurksulgudes viited, nt [9: 5] või [9 lk 5]',
        'type'   : 'brackets_ref',
        '_priority_': (0, 0, 3, 1),
        '_regex_pattern_': re.compile(\
            r'''
            (\[\s?                          # starts with '['
                (\d+\s[^\ \[\]]{1,2}\s\d+|  # a) numbers + space + few non-spaces + space + numbers, or
                 \d+:\s?\d+|                # b) numbers + colon + space + numbers, or
                 \d+,\d+|                   # c) numbers + comma + numbers, or
                 \d+)                       # d) only numbers
            \s?\])                          # ends with ']'
            ''', re.X),
        '_group_': 1 },\
      { 'comment': 'Captures content inside square brackets #2 (non-numeric stuff);',
        'example': 'Nt [Viide2006]',
        'type'   : 'brackets',
        '_priority_': (0, 0, 3, 2),
        '_regex_pattern_': re.compile(\
            r'''
            (\[                              # starts with '['
                (?!at\]|\s?\d)               # look-ahead: not '[at]' (inside e-mail) nor number
                [^\s\[\]]+                   # sequence of non-whitespace/non-brackets symbols 
            \])                              # ends with ']'
            ''', re.X),
        '_group_': 1 },\
        
      # Partly based on PATT_12 from https://github.com/EstSyntax/preprocessing-module 
      #                          and https://github.com/kristiinavaik/ettenten-eeltootlus 
      { 'comment': 'Captures parenthesis that contain a numeric range, and less than 3 surrounding words;',
        'example': '(600–800 sõna) või (u AD 450–1050) või ( 2.03.1900 -16.09.1975 )',
        'type'   : 'parenthesis_num_range',
        '_priority_': (0, 0, 4, 1),
        '_regex_pattern_': re.compile(\
            r'''
            (\(                                    # starts with '('
                (?![^()]*'''+_three_lc_words+''')  # look-ahead: block if there are 3 lowercase words
                [^()]*                             # some content after range (optional)
                \d+\s*\.?\s*                       # first number
                '''+_hyphen_pat+'''+               # hyphen, dash etc.
                \d+\s*\.?\s*                       # second number
                (?![^()]*'''+_three_lc_words+''')  # look-ahead: block if there are 3 lowercase words
                [^()]*                             # some content after range (optional)
            \))                                    # ends with ')'
            ''', re.X),
        '_group_': 1 },\
      { 'comment': 'Captures parenthesis that likely contain date/time;',
        'example': '(22.08.2010 18:11:32)',
        'type'   : 'parenthesis_datetime',
        '_priority_': (0, 0, 4, 2),
        '_regex_pattern_': re.compile(\
            r'''
            (\(\s*                                 # starts with '('
                (?![^()]*'''+_three_lc_words+''')  # look-ahead: block if there are 3 lowercase words
                (?=[^()]*[12][05-9]\d\d)           # look-ahead: require a year-like number
                (?=[^()]*'''+_clock_time+''')      # look-ahead: require a clock-time-like number
                [^()]*                             # some content (different date formats possibly)
            \s*\))                                 # ends with ')'
            ''', re.X),
        '_group_': 1 },\
      { 'comment': 'Captures parenthesis that likely contain a reference with year number;',
        'example': '( PM 3.02.1998 ) või ( “ Kanuu ” , 1982 ) või ( Looming , 1999 , nr.6 )',
        'type'   : 'parenthesis_ref',
        '_priority_': (0, 0, 4, 3),
        '_regex_pattern_': re.compile(\
            r'''
            (\(\s*                                 # starts with '('
                ['''+_uc_letter+_start_quotes+'''] # titlecase word, or starting quotes
                (?![^()]*'''+_three_lc_words+''')  # look-ahead: block if there are 3 lowercase words
                (?=[^()]*[12][05-9]\d\d)           # look-ahead: require a year-like number
                [^()]*                             # content
            \s*\))                                 # ends with ')'
            ''', re.X),
        '_group_': 1 },\
        
      #{ 'comment': 'Captures TODO',
      #  'example': '',
      #  'type'   : 'parenthesis_ref',
      #  '_priority_': (0, 0, 4, 1),
      #  '_regex_pattern_': re.compile(\
      #      r'''
      #      (\(                                                        # starts with '('
      #        [^()]+                                                   # non-parenthesis
      #        (                                                        #
      #           \s*\d+\.?\s*                                          # a number (potentially year)
      #        )                                                        #
      #      \))                                                        # ends with ')'
      #      ''', re.X),
      #},
      
]


# ===================================================================

class SyntaxIgnoreTagger(Tagger):
    description = 'Tags text snippets that should be ignored during the syntactic analysis.'
    layer_name  = 'syntax_ignore'
    attributes  = ('type')
    depends_on  = ['words', 'sentences']
    configuration = None

    def __init__(self, allow_loose_match:bool = True):
        self.configuration = {'allow_loose_match': allow_loose_match,}
        # Populate vocabulary
        patterns = []
        for ignore_pat in ignore_patterns:
            patterns.append( ignore_pat )
        # Create a new tagger
        self._syntax_ignore_tagger = RegexTagger(vocabulary=patterns,
                                   attributes=[ '_priority_', 'type' ],
                                   conflict_resolving_strategy="MAX",
                                   overlapped=False,
                                   layer_name='syntax_ignore_hints',
                                   )


    def tag(self, text: 'Text', return_layer=False) -> 'Text':
        ''' Tag syntax_ignore layer. '''
        # *) Apply tagger
        conflict_status = {}
        new_layer = self._syntax_ignore_tagger.tag( \
                    text, return_layer=True, status=conflict_status )

        # *) Create an alignment between words and spans
        wid = 0
        ignored_words_spans = []
        for sp in new_layer.spans:
            # Find words that fall within the span
            words_start = -1
            words_end   = -1
            current_wid = wid
            while current_wid < len(text.words):
                word = text.words[current_wid]
                # Exact match
                if word.start == sp.start:
                    words_start = current_wid
                if word.end   == sp.end:
                    words_end = current_wid
                if words_start != -1 and words_end != -1:
                    break
                # Loose match (if allowed)
                if self.configuration['allow_loose_match']:
                    if word.start <= sp.start and sp.start <= word.end:
                        words_start = current_wid
                    if word.start <= sp.end and sp.end <= word.end:
                        words_end = current_wid
                if sp.end < word.start:
                    break
                current_wid += 1
            if words_start != -1 and words_end != -1:
                # Record ignored words
                new_spanlist = SpanList()
                new_spanlist.spans = text.words[words_start:words_end+1]
                new_spanlist.type = sp.type
                ignored_words_spans.append( new_spanlist )
                #print('*',text.text[sp.start:sp.end], sp.start, sp.end)
                #print(text.words[words_start].start, text.words[words_end].end, new_spanlist.spans)
                # Advance in text
                wid = current_wid + 1

        # *) Finally: create a new layer and add spans to the layer
        layer = Layer(name=self.layer_name,
                      parent = 'words',
                      attributes=self.attributes,
                      ambiguous=False)
        for span in ignored_words_spans:
            layer.add_span( span )

        if return_layer:
            return layer
        text[self.layer_name] = layer
        return text

import collections
from typing import Any, Union, Sequence
import itertools

from estnltk import Span, AmbiguousSpan


class EnvelopingSpan(collections.Sequence):
    def __init__(self,
                 spans,
                 layer=None,
                 attributes=None
                 ) -> None:
        spans = tuple(spans)
        assert all(isinstance(span, (Span, AmbiguousSpan, EnvelopingSpan)) for span in spans)
        self.spans = spans

        self._layer = layer

        if attributes is None:
            attributes = {}
        assert isinstance(attributes, dict), attributes
        self._attributes = attributes

        self.parent = None  # type:Union[Span, None]

        # placeholder for dependant layer
        self._base = None  # type:Union[Span, None]

    def get_attributes(self, items):
        r = []
        for x in zip(*[[i
                        if isinstance(i, (list, tuple))
                        else itertools.cycle([i]) for i in getattr(self, item)] for item in items]

                     ):

            quickbreak = all(isinstance(i, itertools.cycle) for i in x)

            tmp = []
            for pair in zip(*x):
                tmp.append(pair)
                if quickbreak:
                    break

            r.append(tmp)
        return r

    @property
    def legal_attribute_names(self) -> Sequence[str]:
        if self.__getattribute__('layer') is not None:
            return self.__getattribute__('layer').__getattribute__('attributes')
        return sorted(self.__getattribute__('_attributes'))

    def to_record(self, with_text=False):
        return [i.to_record(with_text) for i in self.spans]

    @property
    def layer(self):
        return self._layer

    @layer.setter
    def layer(self, value):
        # assert isinstance(value, Layer) or value is None
        self._layer = value

    @property
    def start(self):
        return self.spans[0].start

    @property
    def end(self):
        return self.spans[-1].end

    @property
    def base_spans(self):
        return tuple(s for span in self.spans for s in span.base_spans)

    @property
    def text(self):
        result = []
        for span in self.spans:
            if isinstance(span, EnvelopingSpan):
                result.extend(span.text)
            else:
                result.append(span.text)
        return result

    @property
    def enclosing_text(self):
        return self.layer.text_object.text[self.start:self.end]

    @property
    def raw_text(self):
        return self.text_object.text

    # TODO
    def html_text(self, margin: int = 0):
        return self.text

    @property
    def _html_text(self):
        rt = self.raw_text
        result = []
        for a, b in zip(self.spans, self.spans[1:]):
            result.extend(('<b>', rt[a.start:a.end], '</b>', rt[a.end:b.start]))
        result.extend(('<b>', rt[self.spans[-1].start:self.spans[-1].end], '</b>'))
        return ''.join(result)

    def __iter__(self):
        yield from self.spans

    def __len__(self) -> int:
        return len(self.__getattribute__(
            'spans'
        ))

    def __contains__(self, item: Any) -> bool:
        return item in self.spans

    def __setattr__(self, key, value):
        if key in {'spans', '_attributes', 'parent', '_base', '_layer'}:
            super().__setattr__(key, value)
        elif key == 'layer':
            super().__setattr__('_layer', value)
        else:
            self._attributes[key] = value

    def __getattr__(self, item):
        if item in {'__getstate__', '__setstate__'}:
            raise AttributeError
        if item == '_ipython_canary_method_should_not_exist_' and self.layer is not None and self is self.layer.spans:
            raise AttributeError

        if item in self._attributes:
            return self._attributes[item]

        if item == getattr(self.layer, 'parent', None):
            return self.parent
        layer = self.__getattribute__('layer')  # type: Layer
        return layer.text_object._resolve(layer.name, item, sofar=self)

    def __getitem__(self, idx: int) -> Union[Span, 'EnvelopingSpan']:
        wrapped = self.spans.__getitem__(idx)
        if isinstance(idx, int):
            return wrapped
        res = EnvelopingSpan(spans=wrapped)
        res.layer = self.layer

        res.parent = self.parent

        return res

    def __lt__(self, other: Any) -> bool:
        return isinstance(other, EnvelopingSpan) and \
            (self.start, self.end, self.spans) < (other.start, other.end, other.spans)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, EnvelopingSpan) \
               and self._attributes == other._attributes \
               and self.spans == other.spans

    def __hash__(self):
        return hash((tuple(self.spans), self.parent))

    def __str__(self):
        return 'ES[{spans}]'.format(spans=',\n'.join(str(i) for i in self.spans))

    def __repr__(self):
        return str(self)

    def _repr_html_(self):
        if self.layer and self is self.layer.spans:
            return self.layer.to_html(header='SpanList', start_end=True)
        return str(self)
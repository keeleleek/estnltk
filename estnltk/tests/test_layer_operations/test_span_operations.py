from estnltk.text import Span
from estnltk.layer.span_operations import touching_right
from estnltk.layer.span_operations import touching_left
from estnltk.layer.span_operations import hovering_right
from estnltk.layer.span_operations import hovering_left
from estnltk.layer.span_operations import right
from estnltk.layer.span_operations import left
from estnltk.layer.span_operations import nested
from estnltk.layer.span_operations import equal
from estnltk.layer.span_operations import nested_aligned_right
from estnltk.layer.span_operations import nested_aligned_left
from estnltk.layer.span_operations import overlapping_left
from estnltk.layer.span_operations import overlapping_right
from estnltk.layer.span_operations import conflict


def test_touching_positions():
    # Example text: 'üks kaks kolmneli viiskuus seitse'
    
    #t = Text('üks kaks kolmneli viiskuus seitse')
    #t.tag_layer(['words'])
    
    # Test on Spans
    span1 = Span(start=0, end=3)    # üks
    span2 = Span(start=4, end=8)    # kaks 
    span3 = Span(start=9, end=13)   # kolm
    span4 = Span(start=13, end=17)  # neli
    span5 = Span(start=18, end=22)  # viis 
    span6 = Span(start=22, end=26)  # kuus
    span7 = Span(start=27, end=33)  # seitse
    
    assert touching_right(span3, span4)
    assert touching_right(span5, span6)
    
    assert touching_left(span4, span3)
    assert touching_left(span6, span5)
    
    assert not touching_left(span1, span2)
    assert not touching_left(span3, span4)


def test_hovering_positions():
    # Example text: 'üks kaks kolmneli viiskuus seitse'
    
    #t = Text('üks kaks kolmneli viiskuus seitse')
    #t.tag_layer(['words'])
    
    # Test on Spans
    span1 = Span(start=0, end=3)    # üks
    span2 = Span(start=4, end=8)    # kaks 
    span3 = Span(start=9, end=13)   # kolm
    span4 = Span(start=13, end=17)  # neli
    span5 = Span(start=18, end=22)  # viis 
    span6 = Span(start=22, end=26)  # kuus
    span7 = Span(start=27, end=33)  # seitse
    
    assert hovering_right(span1, span2)
    assert not hovering_right(span3, span4)
    
    assert hovering_left(span7, span6)
    assert hovering_left(span5, span4)
    
    assert not hovering_left(span6, span5)


def test_left_and_right_positions():
    # Example text: 'üks kaks kolmneli viiskuus seitse'
    
    #t = Text('üks kaks kolmneli viiskuus seitse')
    #t.tag_layer(['words'])
    
    # Test on Spans
    span1 = Span(start=0, end=3)    # üks
    span2 = Span(start=4, end=8)    # kaks 
    span3 = Span(start=9, end=13)   # kolm
    span4 = Span(start=13, end=17)  # neli
    span5 = Span(start=18, end=22)  # viis 
    span6 = Span(start=22, end=26)  # kuus
    span7 = Span(start=27, end=33)  # seitse
    
    assert right(span1, span2)
    assert not right(span3, span1)
    
    assert left(span7, span6)
    assert left(span4, span3)
    
    assert not left(span6, span7)


def test_nested_positions():
    # Example text: 'üks kaks kolmneli viiskuus seitse'
    
    #t = Text('üks kaks kolmneli viiskuus seitse')
    #t.tag_layer(['words'])
    
    # Test on Spans
    span1  = Span(start=0, end=3)    # üks
    span2  = Span(start=4, end=8)    # kaks 
    span3  = Span(start=9, end=13)   # kolm
    span4  = Span(start=13, end=17)  # neli
    span34 = Span(start=9, end=17)   # kolmneli
    span5  = Span(start=18, end=22)  # viis 
    span6  = Span(start=22, end=26)  # kuus
    span56 = Span(start=18, end=26)  # viiskuus
    span7  = Span(start=27, end=33)  # seitse
    
    assert nested(span56, span6)
    assert not nested(span34, span5)
    
    assert nested(span34, span3)
    assert nested(span34, span4)
    
    assert not nested(span34, span5)


def test_nested_aligned_positions():
    # Example text: 'üks kaks kolmneli viiskuus seitse'
    
    #t = Text('üks kaks kolmneli viiskuus seitse')
    #t.tag_layer(['words'])
    
    # Test on Spans
    span1  = Span(start=0, end=3)    # üks
    span2  = Span(start=4, end=8)    # kaks 
    span3  = Span(start=9, end=13)   # kolm
    span4  = Span(start=13, end=17)  # neli
    span34 = Span(start=9, end=17)   # kolmneli
    span5  = Span(start=18, end=22)  # viis 
    span6  = Span(start=22, end=26)  # kuus
    span56 = Span(start=18, end=26)  # viiskuus
    span7  = Span(start=27, end=33)  # seitse
    
    assert nested_aligned_right(span56, span6)
    assert nested_aligned_right(span34, span4)
    assert not nested_aligned_right(span34, span5)
    assert not nested_aligned_right(span34, span7)
    
    assert nested_aligned_left(span34, span3)
    assert not nested_aligned_left(span34, span4)


def test_overlapping_positions():
    # Example text: 'üks kaks kolmneli viiskuus seitse'
    
    #t = Text('üks kaks kolmneli viiskuus seitse')
    #t.tag_layer(['words'])
    
    # Test on Spans
    span1  = Span(start=0, end=3)    # üks
    span2  = Span(start=4, end=8)    # kaks 
    span3  = Span(start=9, end=13)   # kolm
    span23 = Span(start=4, end=13)   # 'kaks kolm'
    span4  = Span(start=13, end=17)  # neli
    span34 = Span(start=9, end=17)   # kolmneli
    span5  = Span(start=18, end=22)  # viis 
    span6  = Span(start=22, end=26)  # kuus
    span56 = Span(start=18, end=26)  # viiskuus
    span7  = Span(start=27, end=33)  # seitse
    span67 = Span(start=22, end=33)  # 'kuus seitse'

    assert overlapping_left(span34, span23)
    assert not overlapping_left(span34, span3)

    assert overlapping_right(span56, span67)
    assert not overlapping_right(span56, span6)


def test_conflict_positions():
    # Example text: 'üks kaks kolmneli viiskuus seitse'
    
    #t = Text('üks kaks kolmneli viiskuus seitse')
    #t.tag_layer(['words'])
    
    # Test on Spans
    span1  = Span(start=0, end=3)    # üks
    span2  = Span(start=4, end=8)    # kaks 
    span3  = Span(start=9, end=13)   # kolm
    span23 = Span(start=4, end=13)   # 'kaks kolm'
    span4  = Span(start=13, end=17)  # neli
    span34 = Span(start=9, end=17)   # kolmneli
    span5  = Span(start=18, end=22)  # viis 
    span6  = Span(start=22, end=26)  # kuus
    span56 = Span(start=18, end=26)  # viiskuus
    span7  = Span(start=27, end=33)  # seitse
    span67 = Span(start=22, end=33)  # 'kuus seitse'
    
    assert conflict(span23, span34)
    assert conflict(span56, span67)
    assert conflict(span34, span3)
    assert conflict(span56, span6)
    assert not conflict(span3, span4)
    assert not conflict(span6, span5)
    assert not conflict(span34, span2)
    assert not conflict(span34, span56)
    assert not conflict(span7, span56)


def test_equal_positions():
    # Example text: 'üks kaks kolmneli viiskuus seitse'
    
    #t = Text('üks kaks kolmneli viiskuus seitse')
    #t.tag_layer(['words'])
    
    # Test on Spans
    span1  = Span(start=0, end=3)    # üks
    span2  = Span(start=4, end=8)    # kaks 
    span3  = Span(start=9, end=13)   # kolm
    span23 = Span(start=4, end=13)   # 'kaks kolm'
    span4  = Span(start=13, end=17)  # neli
    span34 = Span(start=9, end=17)   # kolmneli
    span43 = Span(end=17, start=9)   # kolmneli
    span5  = Span(start=18, end=22)  # viis 
    span6  = Span(start=22, end=26)  # kuus
    span56 = Span(start=18, end=26)  # viiskuus
    span7  = Span(start=27, end=33)  # seitse
    span67 = Span(start=22, end=33)  # 'kuus seitse'
    
    assert equal(span34, span43)
    assert not equal(span34, span56)
    assert not equal(span34, span3)

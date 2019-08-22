# Jembatan
Jembatan is a pythonic framework for working with annotations and features in text and natural language processing.  
It borrows heavily from the `CAS` and `AnalysisEngine` concepts in [UIMA](https://uima.apache.org/),
`Slab` and `AnalysisFunction` in [Chalk](https://uima.apache.org/) and [Epic](https://github.com/dlwh/epic) as well as the querying and pipeline conveniences found in [uimafit](https://github.com/apache/uima-uimafit) and [ClearTk](https://cleartk.github.io/cleartk/).

## About the name
The word for bridge in Bahasa Indonesia (aka Indonesian) is *jembatan*, and was chosen to represent how
this library aims to bridge and span the many disparate natural language processing frameworks into common
data structures, pipelines and types systems for analysis.

## License ##
Jembatan is distributed under [Apache License, version 2.0](http://www.apache.org/licenses/LICENSE-2.0.html)

## Goals ##
Jembatan aims to make analyses of documents accessible through a data structure known as a `Spandex`.  This is essentially a contained for putting Annotation spans over texts.  Text processing can then be thought of as a series of functions that accept and decorate a spandex with
new annotations.

## Hello Jembatan ##

This example shows how to quickly run Jembatan's [SpacyNLP](http://spacy.io) wrapper on a block of text and display some analyses:

```python
import spacy

from spacy.en import English
from jembatan.core.spandex import (Span, Spandex)
from jembatan.analyzers.spacy import SpacyAnalyzer
from jembatan import typesys as jemtypes


# initialize Spandex with document text
spndx = Spandex("""Education is all a matter of building bridges. 
    When one burns one's bridges, what a very nice fire it makes""")

# initialize and run Spacy on Spandex
# the SpacyAnalyzer will add annotations for Sentences, Tokens, DependencyParses and more.
en_nlp = spacy.load("en_core_web_sm")
spacy_analyzer = SpacyAnalyzer(en_nlp)
spacy_analyzer(spndx)

# Query and print annotations
for i,  sent in enumerate(spndx.select(jemtypes.Sentence)):
    print("Sentence {:d}: {}".format(i, spndx.spanned(sent)))
    for j, tok in enumerate(spndx.covered(typesys.Token, sentspan)):
        toktext = spndx.spanned(tok)
        print("\t {:d}\t{}\t{}".format(j, toktext, tok.pos))
```

Produces the following output:
```
Sentence 0: Education is all a matter of building bridges. 
	 0	Education	NN
	 1	is	VBZ
	 2	all	PDT
	 3	a	DT
	 4	matter	NN
	 5	of	IN
	 6	building	VBG
	 7	bridges	NNS
	 8	.	.
Sentence 1: When one burns one's bridges, what a very nice fire it makes
	 0	When	WRB
	 1	one	PRP
	 2	burns	VBZ
	 3	one	PRP
	 4	's	POS
	 5	bridges	NNS
	 6	,	,
	 7	what	WDT
	 8	a	DT
	 9	very	RB
	 10	nice	JJ
	 11	fire	NN
	 12	it	PRP
	 13	makes	VBZ
```

## Tutorial

### Spans and Spandex
A `Span` is essentially a tuple with a `begin` and `end` field which (presumably) define character offsets.  Spans
are comparable, to allow for indexing and fast retrieval relative to other Spans.

The `Spandex` is the central data structure through which all analyses in
Jembatan pass.  The Spandex houses layers of spans plus annotations over 
different views of a document/resource.  Typically Jembatan pipelines 
are formed by passing the same Spandex objects to multiple analyzers.

To get a better idea of these capabilities let's play with the Spandex
APIs.

```python
from jembatan.core.spandex import (Span, Spandex)

# Create Spandex initialized with text
spndx = Spandex("Up until this point we resisted the urge to make a reference to lycra and hot pants.")

# you can construct Spans in two ways
up_span = Span(begin=0, end=2)
this_span = Span(10, 14)

# print text of up_span.  Should yield 'Up' in both cases
# method 1
print(spndx.spanned_text(up_span))

# method 2
print(up_span.spanned_text(spndx))

# print text of this_span
print(spndx.spanned_text(this_span)
```

### Typesystem and Annotations
Spans are useful, but usually we want to attach some sort data to the Span.  For example in named entity recognition
we may want to know if the Span is a location, place or organization.

Annotations are implemented as python dataclasses and are paired with Spans when getting indexed into a Spandex.
Jembatan has a basic NLP typesystem defined in `jembatan.typesys` including common  like `Token`, `Sentence`, `DependencyNode`, etc...
The `Annotation` class inherits from `Span` and so it can be used for any `Spandex` query in the same way you would use a span.

#### Defining your own types
You can define your own types by inheriting from `jemtypes.Annotation` and decorating it with the `@dataclass`.  Read the [dataclasses documentation](https://docs.python.org/3/library/dataclasses.html) to learn more about defining fields
with defaults and type hints.

```
from dataclasses import dataclass
import jembatan.typesys as jemtypes

@dataclass
class Lycra(jemtypes.Annotation):
    index: int = 0
```

Referring back to the Spandex example above, we can annotate it with an occurence of Lycra as follows:
```python
lycra = Lycra(begin=64, end=69, index=0)

spndx.add_annotations(Lycra, lycra)
```

If you would like to define types that link to other types, we suggest using `jemtypes.AnnotationRef` as it limits
exposure to heavy recursion during serialization.  

A toy example is shown below, a more real world example can be found
in the definition of `jemtypes.syntax.DependencyNode` and `jemtypes.syntax.DependencyEdge`.

```python
@dataclass
class HotPants(jemtypes.Annotation):
    lycra_ref: jemtypes.AnnotationRef[Lycra] = None


    @jemtypes.AnnotationRef.deref_property
    def lycra(self):
        return self.lycra_ref

    @lycra.setter
    def lycra(self, val: Lycra):
        self.lycra_ref = AnnotationRef(obj=val)
```

And to instantiate and populate a HotPants instance
```python
    lycra_ref = jemtypes.AnnotationRef(lycra)
    hot_pants = HotPants(begin=74, end=83, lycra_ref=lycra_ref)
```

Notice that the HotPants class has a getter and setter for a property named lycra.  The `deref_property` decorator provides
mechanisms to aid in working with `AnnotationRef` fields in your class.  Using the lycra properties the above code can be written:
```python
    hot_pants = HotPants(begin=74, end=83)
    hot_pants.lycra = lycra

    assert hot_pants.lycra == hot_pants.lycra_ref.obj
```

### Analysis Functions

In line with Python's duck typing, an Analysis Function is any object or function that implements `__call__(spndx, **kwargs)`.  Analysis
Functions are permitted lots of room.  Some may simply query the 
Spandex for information, more commonly they will annotate one or 
more views of the text and write out information for other use.

#### Function-based
For the purposes of illustration, let's create functions that
annotate the text with mentions of lycra or hot pants.

```
import re
from collections import namedtuple


def lycra_analyzer(spndx, **kwargs):
    lycra_re = re.compile("(lycra)". re.IGNORECASE)

    # Find matches for regex above
    mentions = []
    for i, m in enumerate(lycra_re.finditer(spndx.content)):
        mention = Lycra(begin=m[0], end=m[1], index=i)
        mentions.append(mention)

    # Add layer of lycra annotation to the Spandex
    spndx.add_layer(Lycra, mentions)

# run the Lycra analyzer
lycra_analyzer(spndx)
```

#### Class-based
For convenience a base Analysis Function can be found at
`jembatan.core.af.AnalysisFunction`.  To define your own,
simply inherit from it, and override the `process` method.

```
from jembatan.core.af import AnalysisFunction

HotPants = namedtuple(idx)
class HotPantsAnalyzer(AnalysisFunction):

    def process(self, spndx, **kwargs):
        hotpants_re = re.compile("(hot pants|hotpants)". re.IGNORECASE)

        # Find matches for regex above
        mentions = []
        for i, m in enumerate(hotpants_re.finditer(spndx.content)):
            mention = HotPants(begin=m[0], end=m[1], index=i)
            mentions.append(mention)

        # Add layer of annotation to the Spandex
        spndx.add_layer(Hotpants, mentions)

# initialize and run hot pants analyzer
hot_pants_analyzer = HotPantsAnalyzer()
hot_pants_analyzer(spndx)
```


#### What about the Keyword Arguments? 

The examples above ignore the `**kwargs` parameter.  These keyword
arguments are included in Analysis Function signatures to provide
a means for altering behavior at runtime.  This enables reuse of components for similar but slightly different behaviors.

A classic use case is specifying a window type / governing annotation
type for a sentence segmenter.  For example, we may have a document is organized under blocks for titles, abstract and sections.  If we only
want to run the segmenter on abstract and sections, we could write
the sentence segmenter analysis function to accept window type `Abstract` or `Section`.   Now instead of constructing separate segmenters
we can reuse them by specifying different window types.


### Back to Spandex Operations

Assuming we've run our Spandex with the analyzers above, we can now
query the structure in several ways.

#### Select
The simplest operation returns all instances of a particular
annotation type from the Spandex along with their spans.


```
lycra_spans = spndx.select(Lycra)
hotpant_spans = spndx.select(HotPants)
```

### Covered / Preceeding / Following
Covered selects all of a type within a span. 
```
covered_tokens = spndx.select_covered(jemtypes.Token, Span(0,20))
```

Preceeding selects all of a type before a span.
```
preceding_tokens = spndx.select_preceeding(jemtypes.Token, Span(0,20))
```

Following selects all of a type after a span.
```
preceding_tokens = spndx.following(jemtypes.Token, Span(0,20))
```

### Retrieving annotation texts
`spanned_text` will return the text contained within the bounds of a span.
```
spndx.spanned_text(Span(0,20))
```


### View Mapping

### Example


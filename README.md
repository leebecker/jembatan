# Jembatan
Jembatan is a pythonic framework for working with annotations typesystems and features in text and natural language processing.  
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

from jembatan.core.spandex import (JembatanDoc, Span, Spandex)
from jembatan.analyzers.spacy import SpacyAnalyzer
from jembatan.typesys.segmentation import Sentence, Token

# creata a JembatanDoc.  Initialize default view with content_string
jemdoc = JembatanDoc(content_string="""Education is all a matter of building bridges. 
    When one burns one's bridges, what a very nice fire it makes""")

# initialize and run Spacy on Spandex
# the SpacyAnalyzer will add annotations for Sentences, Tokens, DependencyParses and more.
en_nlp = spacy.load("en_core_web_sm")
spacy_analyzer = SpacyAnalyzer(en_nlp)
spacy_analyzer(jemdoc)

# Query and print annotations from default view
spndx = jemdoc.default_view
for i,  sent in enumerate(spndx.select(Sentence)):
    print("Sentence {:d}: {}".format(i, spndx.spanned_text(sent)))
    for j, tok in enumerate(spndx.select_covered(Token, sent)):
        toktext = spndx.spanned_text(tok)
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

### JembatanDocs, Spans and Spandex

In jembatan, Documents or artifacts are defined using the `JembatanDoc` class.  This is a top-level container,
which manages metadata (IDs, paths, source, etc) as well as views of the data.

Views are a way to organize around different concerns of the document.  For example a given resource may have one view
that contains the raw HTML, another view with the plain text.  Or in machine translation, one can imagine some artifact
containing both the input text and the output text as different views.  Views are backed by the `Spandex` object, which
are defined by a `name`, `content_string`, `content_mime`. Views also provide the mechanism for collecting, indexing and
querying annotations over the view.

A `Span` is essentially a tuple with a `begin` and `end` field which (presumably) define character offsets.  Spans
are comparable to allow for indexing and fast retrieval relative to other Spans.

Typically Jembatan pipelines are formed by passing the same JembatanDoc objects to multiple analyzers.

To get a better idea of these capabilities let's play with the jembatan APIs.

```python
from jembatan.core.spandex import (JembatanDoc, Span, Spandex)

# Create JembatanDoc initialized with text in default view
jemdoc = JembatanDoc(content_string="Up until this point we resisted the urge to make a reference to lycra and hot pants.")

# get default view
spndx = jemdoc.default_view

# you can construct Spans in two ways
up_span = Span(begin=0, end=2)
this_span = Span(9, 14)

# print text of up_span.  Should yield 'Up' in both cases
# method 1
print(spndx.spanned_text(up_span))

# method 2
print(up_span.spanned_text(spndx))

# print text of this_span
print(spndx.spanned_text(this_span))
```

### Typesystem and Annotations
Spans are useful, but usually we want to attach some sort data to the Span.  For example in named entity recognition
we may want to know if the Span is a location, place or organization.

The Jembatan mechanism for attached data to a spandex comes by way of Annotations.  You can think of an Annotation as
a data struct associated with some scope over a spandex view.  Under the hood, Annotations extend native python 3 dataclasses, which
provides a useful convention for authoring new annotation types and for getting/setting an instance's properties.

Jembatan has a basic NLP typesystem defined in `jembatan.typesys` including common  like `Token`, `Sentence`, `DependencyNode`, etc...

#### Annotation Scope
Jembatan has defined three base classess that correspond to different annotation scopes.  `Annotation` is the base class and has scope `UNKNOWN`.
Most type systems will not inherit from Annotation.

The `SpannedAnnotation` class inherits from `Span` and `Annotation` and has scope `SPAN`.  Like `Span`, `SpannedAnnotation` has both `begin`
and `end` properties.  This makes it useful for passing into any of the spandex queries/methods that accept a `Span` argument.  
For most tasks the majority of types will inherit from `SpannedAnnotation`

The `DocumentAnnotation` has scope `DOCUMENT`, and is useful for defining document level properties without requiring a `begin` and `end` field.

### Predefined Types
and are paired with Spans when getting indexed into a Spandex.

#### Defining your own types
You can define your own types by inheriting from `jemtypes.SpannedAnnotation` or `jemtypes.DocumentAnnotation`.  Read the [dataclasses documentation](https://docs.python.org/3/library/dataclasses.html) to learn more about defining fields with defaults and type hints.  The serialization methods
only support definition of fields as combination of primitive types, lists, dicts, or other Annotation types.

```
from dataclasses import dataclass
import jembatan.typesys as jemtypes

class Lycra(jemtypes.SpannedAnnotation):
    index: int = 0
```

Referring back to the Spandex example above, we can annotate it with an occurence of Lycra as follows:
```python
lycra = Lycra(begin=64, end=69, index=0)

spndx.add_annotations(lycra)
```

Annotations can refer to other annotations.  This mechanism is used create tree and graph structures common to many linguistic representations.

A toy example is shown below, a more real world example can be found in the definition of 
`jemtypes.syntax.DependencyNode` and `jemtypes.syntax.DependencyEdge`.

```python
@dataclass
class HotPants(jemtypes.Annotation):
    lycra: jemtypes.[Lycra] = None
```

And to instantiate and populate a HotPants instance
```python
    hot_pants = HotPants(begin=74, end=83, lycra=lycra)
```


### Views

As mentioned above `JembatanDoc` maps names to a collection of `Spandex` backed views.

```python

from jembatan.core.spandex import JembatanDoc

jemdoc = JembatanDoc()
jemdoc.default_view.content_string = "Some text for the default view"

other_view_name = "otherView"
other_view = jemdoc.create_view(other_view_name, "Some text for the other view")

print("Default View Text via get_view method:\n", jemdoc.get_view("_SpandexDefaultView").content_string)
print("Default View Text via default_view attribute:\n", jemdoc.default_view.content_string)
print("Other View Text via get_view method:\n", jemdoc.get_view(other_view_name).content_string)
```


### Analysis Functions

In line with Python's duck typing, an Analysis Function is any object or function that implements `__call__(jemdoc: JembatanDoc, **kwargs)`.  Analysis
Functions are permitted lots of room.  Some may simply query the 
Spandex for information, more commonly they will annotate one or 
more views of the text and write out information for other use.

#### Function-based
For the purposes of illustration, let's create functions that
annotate the text with mentions of lycra or hot pants.

```python
import re
from collections import namedtuple


def lycra_analyzer(jemdoc, **kwargs):
    spndx = jemdoc.default_view
    lycra_re = re.compile("(lycra)". re.IGNORECASE)

    # Find matches for regex above
    mentions = []
    for i, m in enumerate(lycra_re.finditer(spndx.content)):
        mention = Lycra(begin=m[0], end=m[1], index=i)
        mentions.append(mention)

    # Add layer of lycra annotation to the Default View Spandex
    spndx.add_annotations(mentions)

# run the Lycra analyzer
lycra_analyzer(jemdoc)
```

#### Class-based
For convenience a base Analysis Function can be found at
`jembatan.core.af.AnalysisFunction`.  To define your own,
simply inherit from it, and override the `process` method.

```python
from jembatan.core.af import AnalysisFunction
from jembatan.core.spandex import JembatanDoc

class HotPantsAnalyzer(AnalysisFunction):

    def process(self, jemdoc: JembatanDoc, **kwargs):
        spndx = jemdoc.default_view
        hotpants_re = re.compile("(hot pants|hotpants)". re.IGNORECASE)

        # Find matches for regex above
        mentions = []
        for i, m in enumerate(hotpants_re.finditer(spndx.content)):
            mention = HotPants(begin=m[0], end=m[1])
            mentions.append(mention)

        # Add layer of annotation to the Spandex
        spndx.add_annotations(mentions)

# initialize and run hot pants analyzer
hot_pants_analyzer = HotPantsAnalyzer()
hot_pants_analyzer(jemdoc)
```

#### Single vs Multi-View Analysis Functions
The majority of Analysis Functions operate solely on the default view and have no need to retrieve or update other views.
Multi-View Analysis Functions on the other hand typically access either views via parameters or static configuration.

The `process_default_view` decorator is provided as a convenience to eliminate the need to query the JembatanDoc for the default view
The HotPants example above can be written more concisely as follows:

```python
from jembatan.core.af import process_default_view, AnalysisFunction
from jembatan.core.spandex import Spandex

class HotPantsAnalyzer(AnalysisFunction):

    @process_default_view
    def process(self, spndx: Spandex, **kwargs):
        hotpants_re = re.compile("(hot pants|hotpants)". re.IGNORECASE)

        # Find matches for regex above
        mentions = []
        for i, m in enumerate(hotpants_re.finditer(spndx.content)):
            mention = HotPants(begin=m[0], end=m[1])
            mentions.append(mention)

        # Add layer of annotation to the Spandex
        spndx.add_annotations(mentions)
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


```python
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


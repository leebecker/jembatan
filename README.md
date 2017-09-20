# Jembatan
Jembatan is the word for bridge in Bahasa Indonesia.  It is also a python based framework
for wrapping and linking the many disparate Natural Language Processing frameworks
into common data structures, pipelines and type systems for analysis.  Jembatan borrows
heavily from the `CAS` and `AnalysisEngine` concepts in [UIMA](https://uima.apache.org/),
`Slab` and `AnalysisFunction` in [Chalk](https://uima.apache.org/) and [Epic](https://github.com/dlwh/epic) as well as the querying and pipeline conveniences found in [uimafit](https://github.com/apache/uima-uimafit) and [ClearTk](https://cleartk.github.io/cleartk/).


## License ##
Jembatan is distributed under [Apache License, version 2.0](http://www.apache.org/licenses/LICENSE-2.0.html)

## Goals ##
Jembatan aims to make analyses of documents accessible through a data structure known as
a `Spandex`.  This is essentially a piece of text that contains `Spans`

## Hello Jembatan ##

This example shows how to quickly run Jembatan's SpacyNLP wrapper on a block of text and display some analyses:

```python
import spacy

from spacy.en import English
from jembatan.core.spandex import (Span, Spandex)
from jembatan.wrappers.spacy import SpacyAnalyzer
from jembatan import typesys as jemtypes


# initialize Spandex with document text
spndx = Spandex("""Education is all a matter of building bridges. 
    When one burns one's bridges, what a very nice fire it makes""")

# initialize and run Spacy on Spandex
en_nlp = English()
spacy_analyzer = SpacyAnalyzer(en_nlp)
spacy_analyzer(spndx)

# Query and print annotations

for i, (sentspan, sentobj) in enumerate(spndx.select(jemtypes.Sentence)):
    print("Sentence {:d}: {}".format(i, spndx.spanned(sentspan)))
    for j, (tokspan, tokobj) in enumerate(spndx.covered(typesys.Token, sentspan)):
        toktext = spndx.spanned(tokspan)
        print("\t {:d}\t{}\t{}".format(j, toktext, tokobj.partOfSpeech.pos))
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

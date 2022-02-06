<img src="images/ninologo.png" align="right" width="200"/>
<img src="images/tf.png" align="right" width="200"/>

# Feature documentation

Here you find a description of the transcriptions of the NinMed corpus,
the Text-Fabric model in general, and the node types, features of these
corpora.

**N.B.** There are several other Akkadian corpora in Text-Fabric, that have been
converted from the plain ATF:
[OldBabylonian](https://github.com/Nino-cunei/oldbabylonian)
and
[OldAssyrian](https://github.com/Nino-cunei/oldassyrian).

For NinMed we have tried to be as consistent as possible with the
conventions use for those corpora, when converting to TF.
See [transcription](https://github.com/Nino-cunei/tfFromAtf/blob/master/docs/transcription.md).

## Conversion from JSON to TF

The Text-Fabric model views the text as a series of atomic units, called
*slots*. In this corpus [*signs*](#sign) are the slots.

On top of that, more complex textual objects can be represented as *nodes*. In
this corpus we have node types for:
[*sign*](#sign),
[*word*](#word),
[*cluster*](#cluster),
[*line*](#line),
[*face*](#face),
[*document*](#document).

The type of every node is given by the feature
[**otype**](https://annotation.github.io/text-fabric/Api/Features/#node-features).
Every node is linked to a subset of slots by
[**oslots**](https://annotation.github.io/text-fabric/Api/Features/#edge-features).

Nodes can be annotated with features. See the table below.

Text-Fabric supports up to three customizable section levels.
In this corpus we use:
[*document*](#document) and [*face*](#face) and [*line*](#line).

# Reference table of features

*(Keep this under your pillow)*

## Node type [*sign*](#sign)

Basic unit containing a single `reading` and/or `grapheme` and zero or more *flags*.

There are several types of sign, stored in the feature `type`.

type | examples | description
------- | ------ | ------
`reading` | `ma` `qa2` | normal cintent sign with a reading (lowercase)
`unknown` | `x` `n` | representation of an unknown sign, the `n` stands for an unknown numeral
`numeral` | `5` `5/6`  | a numeral, either with a repeat or with a fraction
`ellipsis` | `...` | representation of an unknown number of missing signs
`erasure` | `° \ °` | representation of an erasure
`grapheme` | `ARAD2` `GAN2` | cintent sign given as a grapheme (uppercase)
`joiner` | `-` `.` | in-word character that joins two content signs
`wdiv` | ` / ` | word divider
`mark` | `[` `(` | any character that is not a reading or grapheme in itself
`lang` | ` %sux %sb %akk ` | language shift
`empty` | | empty sign, usually due to an empty line

feature | example values | description
------- | ------ | ------
**after** | `-` ` ` | what comes after a sign before the next sign
**atf** | `lam` `GIG` |  full atf of a sign
**collated** | `1` | indicates the presence of the *collated* flag `*`
**comment** | `(erased line)` | value of a comment
**damage** | `1` | indicates the presence of the *damage* flag `#`
**det** | `1` | indicates whether the sign is (part of) a determinative, marked by being within braces `{ }`
**excised** | `1` | whether a sign is excised by the editor, marked by being within double angle brackets  `<< >>`
**grapheme**| `GIG` | the grapheme name of a [*sign*](#sign) when its atf is capitalized
**lang** | `sux` `akk` `sb` | language shift: `sux` = Sumerian; `akk` = Akkadian; `sb` = Standard Babylonian
**missing** | `1` | whether a sign is missing, marked by being within square brackets  `[ ]`
**question** | `1` | indicates the presence of the *question* flag `?`
**reading** | `lam` | reading (lowercase) of a sign
**remarkable** | `1` | indicates the presence of the *remarkable* flag `!`
**sym**| `lam` `GIG` | essential parts of a sign, composed of **reading**, **grapheme**
**supplied** | `1` | whether a sign is supplied by the editor, marked by being within angle brackets  `< >`
**type** | type of sign, see table above
**uncertain** | `1` | whether a sign is uncertain, marked by being within brackets  `( )`

## Node type [*word*](#word)

Sequence of signs separated by `-`. Sometimes the `-` is omitted.
There can also be other characters between two signs, such as `.`, called *joiners*.
Words themselves are separated by spaces.

feature | example values | description
------- | ------ | ------
**after** | ` ` | | what comes after a word before the next word, including word dividers
**atf**| `šu-ru-uš#` | full atf of a word, including flags and clustering characters, but no word dividers
**sym**| `šu-ru-uš` | essential parts of a word, composed of the **sym** values of its individual signs

## Node type [*cluster*](#cluster)

Grouped sequence of [*signs*](#sign). There are different
types of these bracketings. Clusters may be nested.
But clusters of different types need not be nested properly with respect to each other.

The type of a cluster is stored in the feature `type`.

type | examples | description
------- | ------ | ------
`langalt` | `_  _` | alternate language
`det` | `{ }` | gloss, determinative
`uncertain` | `( )` | uncertain
`missing` | `[ ]` | missing
`supplied` | `< >` | supplied by the editor in order to get a reading
`excised` | `<< >>` | excised by the editor in order to get a reading

Each cluster induces a sign feature with the same name as the type of the cluster,
which gets value 1 precisely when the sign is in that cluster.

## Node type [*line*](#line)

Subdivision of a containing [*face*](#face).
Corresponds to a transcription or comment line in the source data.

feature | example values | description
------- | ------ | ------ | -----------
**col** | `1` | number of the column in which the line occurs; without prime, see also `primecol`
**ln** | `1` | ATF line number of a numbered transcription line; without prime, see also `primeln`
**lln** | `1` | logical line number within a face: a number from 1 to the number of lines on the face
**lnno** | `1:1` | combination of **col**, **primecol**, **ln**, **primeln** to identify a line
**primecol** | `1` | whether the column number has a prime `'`
**primeln** | `1` | whether the line number has a prime `'`
**atf**| `1'. D[U₃.DU₃.BI ...]` | full atf of a line
**trans** | `1` | indicates whether a line has a translation (in the form of a following meta line (`#tr.en`))
**tr@en** | `If a man suffers from phlegm` | English translation in the form of a meta line (`#tr.en`)

## Node type [*face*](#face)

One of the sides of an *object* belonging to a document [*document*](#document).
In most cases, the object is a *tablet*, but it can also be an *envelope*, or yet an other kind of object. 

feature | example values | description
------- | ------ | ------ | -----------
**face** | `obverse` `reverse` | type of face

## Node type [*document*](#document)

The main entity of which the corpus is composed, representing the transcription
of all objects associated with it.

feature | values | in ATF | description
------- | ------ | ------ | -----------
**collection** | `Kuyunjik` | the collection in which a document is included
**description** | `Fragment of a clay tablet` | short description
**docnumber** | `K.11317` | identification
**museum** | `The British Museum` | name of the museum that holds the tablet
**pnumber** | `P285136` | P-number identification
**publication** | `Edition by NinMed` | publication info

# Slots

Slots are the textual positions. They can be occupied by individual signs.

We discuss the node types we are going to construct. A node type corresponds to
a textual object. Some node types will be marked as a section level.

## Sign

This is the basic unit of writing.

**The node type sign is our slot type in the Text-Fabric representation of this corpus.**

All signs have the features **sym** and **atf** and **after**.

Together they are the building blocks by which the complete original ATF sequence for that sign
can be reconstructed:

*    **atf** + **after** (full representation)
*    **sym** + **after** (plain representation, without modifiers, flags and clusters)

For analytical purposes, there is a host of other features on signs, depending on the type of sign.

### Flags and modifiers ###

Signs may have *flags*.
In transcription they show up as a special trailing character.
Flags code for signs that are damaged, questionable (in their reading), remarkable, or collated.

*   `*` collated 
*   `!` remarkable 
*   `?` question 
*   `#` damage 

Signs may have modifiers: `@v`.

# The other nodes

## Cluster

One or more signs may be bracketed by `( )` or by `[ ]` or by `< >` or by `<< >>` or by `{( )}` or by `{ }`:
together they form a *cluster*.

Each pair of boundary signs marks a cluster of a certain type.
This type is stored in the feature **type**.

Clusters are not be nested in clusters of the same type.

Clusters of one type in general do not respect the boundaries of clusters of other types.

Clusters do not cross line boundaries.

Clusters may contain just one sign.

In Text-Fabric, cluster nodes are linked to the signs it contains.
So, if `c` is a cluster, you can get its signs by 

    L.d(c, otype='sign')

More over, every type of cluster corresponds to a numerical feature on signs with the same name
as that type.
It has value `1` for those signs that are inside a cluster of that type and no value otherwise.

*   `{ }` **det** determinatives
*   `{( )}` **gloss** glosses
*   `( )` **uncertain** uncertain readings
*   `[ ]` **missing** missing signs
*   `<< >>` **excised** signs that have been excised by the editor in order to arrive at a reading
*   `< >` **supplied** signs that have been supplied by the editor in order to arrive at a reading

## Word

Words are sequences of signs joined by `-` or occasionally `.`
Words themselves are separated by spaces ` `.

They only have features: **sym**, **atf**, **after** and **type**, much like the features
with the same name for individual signs.

The last word of a line as the value `\n` in its feature **after**.

## Line

**This node type is section level 3**

A node of type *line* corresponds to a numbered line with transcribed material.

Lines that start with a `#` are comments to the previous line or metadata to the document.
Their contents are turned into document and line features, they do not give rise
to line nodes.

Lines get a column number from preceding `@column i` lines (if any), and this gets stored in 
**col**.

There is no node type corresponding to columns.

The ATF number at the start of the line goes into **ln**, without the `.`.

If primes `'` are present on column numbers and line numbers, they will not get stored on
**col** and **ln**, but instead the features **primcol** and **primeln** will receive a `1`.

If a line has a translation, say in English, marked by a following line starting with 
`#tr.en:`, then the contents of the translation will be added to **tr@en**.

If a line has any translation at all, in whatever language, the feature **trans** becomes `1`.

## Face

**This node type is section level 2**

Lines are grouped into faces.

Faces are marked by lines like

    @obverse

or

    @reverse

A node of type *face* corresponds to the material after a *face* specifier and
before the next *face* specifier or the end of document.

The resulting face type is stored in the feature **face**.

## Document

**This node type is section level 1.**

Faces are grouped into *documents*.

This corpus is just a set of *documents*. The position of a particular document in
the whole set is not meaningful. The main identification of documents is by their
**pnumber**,
not by any sequence number within the corpus.

# Text formats

The following text formats are defined (you can also list them with `T.formats`).

format | kind | description
--- | --- | ---
`text-orig-full` | plain | the full atf, including flags and cluster characters
`text-orig-plain` | plain | the essential bits: readings, graphemes, repeats, fractions, operators, no clusters, flags, inline comments
`layout-orig-full` | layout | as `text-orig-full` but the flag and cluster information is visible in layout
`layout-orig-plain` | layout | as `text-orig-plain` but the flag and cluster information is visible in layout

The formats with `text` result in strings that are plain text, without additional formatting.

The formats with `layout` result in pieces html with css-styles; the richness of layout enables us to code more information
in the plain representation, e.g. blurry characters when signs are damaged or uncertain.

See also the showcases: 
*   [display](https://nbviewer.jupyter.org/github/Nino-cunei/ninmed/blob/master/tutorial/display.ipynb).


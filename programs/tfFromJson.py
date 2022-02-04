import sys
import os
import re
import json
import yaml
from shutil import rmtree

from tf.fabric import Fabric
from tf.convert.walker import CV

HELP = """
python3 tfFromJson.py
    Generate TF and if successful, load it
python3 tfFromJson.py -skipgen
    Load TF
python3 tfFromJson.py -skipload
    Generate TF but do not load it
"""

GH = os.path.expanduser("~/github")
ORG = "Nino-cunei"
REPO = "ninmed"
REPO_DIR = f"{GH}/{ORG}/{REPO}"
REPORT_DIR = f"{REPO_DIR}/report"
DECL_PATH = f"{REPO_DIR}/yaml"
META_DECL_FILE = f"{DECL_PATH}/meta.yaml"

LINE_TYPES = set(
    """
    EmptyLine
    TextLine
    ColumnAtLine
    DiscourseAtLine
    SurfaceAtLine
    ControlLine
    NoteLine
    TranslationLine
    LooseDollarLine
    RulingDollarLine
    SealDollarLine
""".strip().split()
)


def readYaml(fileName):
    if os.path.exists(fileName):
        with open(fileName) as y:
            y = yaml.load(y, Loader=yaml.FullLoader)
    else:
        y = {}
    return y


META_DECL = readYaml(META_DECL_FILE)
VERSION_SRC = META_DECL["versionSrc"]
VERSION_TF = META_DECL["versionTf"]

IN_DIR = f"{REPO_DIR}/source/json/{VERSION_SRC}"
TF_DIR = f"{REPO_DIR}/tf"
OUT_DIR = f"{TF_DIR}/{VERSION_TF}"

META_FIELDS = {
    "collection": ("collection", "str"),
    "description": ("description", "str"),
    "museum.name": ("museum", "str"),
    "cdliNumber": ("pnumber", "str"),
    "number": ("docnumber", "str"),
    "publication": ("publication", "str"),
}


flagging = {
    "*": "collated",
    "!": "remarkable",
    "?": "question",
    "#": "damage",
}

clusterType = dict(
    BrokenAway="missing",  # [ ]
    PerhapsBrokenAway="uncertain",  # ( )
    Removal="excised",  # << >>
    AccidentalOmission="supplied",  # < >
    DocumentOrientedGloss="gloss",  # {( )}
    Determinative="det",  # { }
    LoneDeterminative="det",  # { }
)

commentTypes = set(
    """
    ruling
    colofon
    note
    comment
    seal
    tr@en
    """.strip().split()
)

languages = set(
    """
    en
""".strip().split()
)

LIGA = "␣"

TRANS_RE = re.compile(r"""@i\{([^}]*)\}""", re.S)

# TF CONFIGURATION

slotType = "sign"

generic = {
    "name": META_DECL["name"],
    "editor": META_DECL["editor"],
    "project": META_DECL["project"],
    "converters": META_DECL["converters"],
}

otext = {
    "fmt:text-orig-full": "{atf}{after}",
    "fmt:text-orig-plain": "{sym}{after}",
    "fmt:text-orig-bare": "{sym}{after}",
    "sectionFeatures": "pnumber,face,lnno",
    "sectionTypes": "document,face,line",
}

intFeatures = (
    set(
        """
        ln
        lln
        col
        number
        primeln
        primecol
        trans
        variant
    """.strip().split()
    )
    | set(flagging.values())
    | set(clusterType.values())
    | {x[1][0] for x in META_FIELDS.items() if x[1][1] == "int"}
)

featureMeta = {
    "after": {"description": "what comes after a sign or word (- or space)"},
    "atf": {
        "description": (
            "full atf of a sign (without cluster chars)"
            " or word (including cluster chars)"
        ),
    },
    "col": {"description": "ATF column number"},
    "collated": {"description": "whether a sign is collated (*)"},
    "collection": {"description": 'collection name from metadata field "collection"'},
    "colofon": {"description": "colofon comment to a line"},
    "comment": {"description": "comment to a line"},
    "damage": {"description": "whether a sign is damaged"},
    "description": {"description": 'description from metadata field "description"'},
    "det": {
        "description": "whether a sign is a determinative gloss - between { }",
    },
    "docnumber": {"description": 'document number from metadata field "number"'},
    "excised": {
        "description": "whether a sign is excised - between << >>",
    },
    "face": {"description": "full name of a face including the enclosing object"},
    "flags": {"description": "sequence of flags after a sign"},
    "gloss": {
        "description": "whether a sign belongs to a gloss - between {( )}",
    },
    "grapheme": {"description": "grapheme of a sign"},
    "lang": {
        "description": (
            "language of a document, word, or sign:"
            " absent: Akkadian; sux: Sumerian; sb: Standard Babylonian"
        )
    },
    "lemma": {
        "description": (
            "lemma of a word:"
            "comma-separated values of the uniqueLemma field in the JSON source"
        )
    },
    "lln": {"description": "logical line number of a numbered line"},
    "ln": {"description": "ATF line number of a numbered line, without prime"},
    "lnno": {
        "description": (
            "ATF line number, may be $ or #, with prime; column number prepended"
        ),
    },
    "missing": {
        "description": "whether a sign is missing - between [ ]",
    },
    "modifiers": {"description": "sequence of modifiers after a sign"},
    "note": {"description": "note comment to a line"},
    "number": {"description": "numeric value of a number sign"},
    "pnumber": {"description": "P number of a document"},
    "primecol": {"description": "whether a prime is present on a column number"},
    "primeln": {"description": "whether a prime is present on a line number"},
    "publication": {
        "description": 'publication info from metadata field "publication"'
    },
    "question": {"description": "whether a sign has the question flag (?)"},
    "reading": {"description": "reading of a sign"},
    "remarkable": {"description": "whether a sign is remarkable (!)"},
    "ruling": {"description": "ruling comment to a line"},
    "seal": {"description": "seal comment to a line"},
    "sym": {"description": "essential part of a sign or of a word"},
    "supplied": {
        "description": "whether a sign is supplied - between < >",
    },
    "trans": {"description": "whether a line has a translation"},
    "tr@en": {"description": "english translation of a line"},
    "type": {"description": "name of a type of cluster or kind of sign"},
    "variant": {
        "description": (
            "if sign is part of a variant pair, "
            "this is the sequence number of the variant (1 or 2)"
        )
    },
    "uncertain": {"description": "whether a sign is uncertain - between ( )"},
    "museum": {"description": 'museum name from metadata field "museum.name"'},
}


def getJsonFiles():
    filePaths = []

    def walk(path):
        with os.scandir(path) as it:
            for entry in it:
                name = entry.name
                if not name.startswith(".") and entry.is_dir():
                    walk(f"{path}/{name}")
                elif name.endswith(".json") and entry.is_file:
                    filePaths.append(f"{path}/{name}")

    walk(IN_DIR)
    return sorted(filePaths)


def readJsonFile(path):
    with open(path) as fh:
        data = json.load(fh)
    return data


def writeReport(fName, lines):
    with open(f"{REPORT_DIR}/{fName}", "w") as fh:
        for line in lines:
            fh.write(f"{line}\n")


def getConverter():
    TF = Fabric(locations=OUT_DIR)
    return CV(TF)


def convert():
    if generateTf:
        if os.path.exists(OUT_DIR):
            rmtree(OUT_DIR)
        os.makedirs(OUT_DIR, exist_ok=True)

    cv = getConverter()

    return cv.walk(
        director,
        slotType,
        otext=otext,
        generic=generic,
        intFeatures=intFeatures,
        featureMeta=featureMeta,
        generateTf=generateTf,
    )


# DIRECTOR


def director(cv):
    debug = False
    curClusters = {cluster: None for cluster in clusterType.values()}

    def info(msg):
        print(f"INFO  ======> {msg}")

    def error(msg, stop=False):
        print(f"ERROR ======> {msg}")
        if stop:
            quit()

    def terminateClusters():
        for tp in curClusters:
            node = curClusters[tp]
            if node:
                cv.terminate(node)
                curClusters[tp] = None

    def doCluster(data, cluster, on=None):
        cv.feature(curSign, type="mark")
        makeOn = data["side"] == "LEFT" if on is None else on
        if makeOn:
            if curClusters[cluster]:
                error(f"cluster {cluster} is nesting", stop=True)
            clusterNode = cv.node("cluster")
            curClusters[cluster] = clusterNode
            cv.feature(clusterNode, type=cluster)
        else:
            clusterNode = curClusters[cluster]
            if clusterNode:
                cv.terminate(clusterNode)
                curClusters[cluster] = None
            else:
                error(f"cluster {cluster} is spuriously closed", stop=True)

    def getClusters():
        return {cluster: 1 for (cluster, node) in curClusters.items() if node}

    def doFlags(data, cur, extraFlag):
        flagList = data.get("flags", [])
        if extraFlag:
            flagList.append(extraFlag)
        if len(flagList):
            flags = "".join(flagList)
            atts = {flagging[flag]: 1 for flag in flags}
            cv.feature(cur, flags=flags, **atts)

    def doModifiers(data, cur):
        modifierList = data.get("modifiers", [])
        if len(modifierList):
            modifiers = "".join(m[1:] for m in modifierList)
            cv.feature(cur, modifiers=f"@{modifiers}")

    def doSign(data, **features):
        nonlocal curSign

        atf = data["value"]
        startMissingInternal = atf != "[" and "[" in atf
        endMissingInternal = atf != "]" and "]" in atf

        extraFlag = ""
        if startMissingInternal or endMissingInternal:
            extraFlag = "#"
            if startMissingInternal:
                atf = atf.replace("[", "") + extraFlag
            if endMissingInternal:
                atf = atf.replace("]", "") + extraFlag

        if endMissingInternal and not startMissingInternal:
            curSign = cv.slot()
            cv.feature(
                curSign,
                atf="]",
                sym="]",
                after=" ",
                **getClusters(),
            )
            doCluster(data, "missing", on=False)

        curSign = cv.slot()

        cv.feature(curSign, atf=atf, **getClusters(), **features)
        doFlags(data, curSign, extraFlag)
        doModifiers(data, curSign)
        signType = data["type"]

        if signType == "AccidentalOmission":
            doCluster(data, clusterType[signType])

        elif signType == "Removal":
            doCluster(data, clusterType[signType])

        elif signType == "BrokenAway":
            doCluster(data, clusterType[signType])

        elif signType == "PerhapsBrokenAway":
            doCluster(data, clusterType[signType])

        elif signType == "UnknownNumberOfSigns":
            sym = data["cleanValue"]
            cv.feature(curSign, type="ellipsis", sym=sym)

        elif signType == "UnidentifiedSign":
            sym = data["cleanValue"]
            cv.feature(curSign, type="unknown", sym=sym)

        elif signType == "UnclearSign":
            sym = data["cleanValue"]
            cv.feature(curSign, type="unknown", sym=sym)

        elif signType == "Number":
            sym = data["cleanValue"]
            cv.feature(curSign, type="number", sym=sym, number=int(sym))

        elif signType == "Logogram":
            sym = data["cleanValue"]
            cv.feature(curSign, type="grapheme", sym=sym, grapheme=sym)

        elif signType == "Reading":
            sym = data["name"]
            cv.feature(curSign, type="reading", sym=sym, reading=sym)

        elif signType == "Joiner":
            sym = data["cleanValue"]
            cv.feature(curSign, type="joiner", sym=sym)

        elif signType == "Determinative" or signType == "Variant":
            error(f"nested {signType} Signs")

        else:
            error(f"unrecognized sign type {signType}")

        if startMissingInternal and not endMissingInternal:
            curSign = cv.slot()
            cv.feature(
                curSign,
                atf="[",
                sym="[",
                after="",
                **getClusters(),
            )
            doCluster(data, "missing", on=True)

    paths = getJsonFiles()
    for (i, path) in enumerate(paths):
        fileName = path.split("/")[-1].rsplit(".", 1)[0]
        docData = readJsonFile(path)
        metaData = {}
        for (origField, (field, tp)) in META_FIELDS.items():
            origFields = origField.split(".", 1)
            metaData[field] = (
                docData[origField]
                if len(origFields) == 1
                else docData[origFields[0]][origFields[1]]
            )
        textData = docData["text"]["allLines"]
        nLines = len(textData)

        print(f"{i + 1:>3} {nLines:>4} lines in {fileName}")
        if nLines == 0:
            continue

        curDoc = cv.node("document")
        cv.feature(curDoc, **metaData)
        curFace = None
        curFaceValue = None
        col = None
        primecol = None
        lln = 0

        prevLine = None

        for lineData in textData:
            lang = None
            lineType = lineData["type"]
            isFaceLine = lineType == "SurfaceAtLine"
            if isFaceLine:
                thisFaceValue = lineData["label"]["surface"].lower()
                if thisFaceValue == curFaceValue:
                    continue

            if isFaceLine or not curFace:
                if isFaceLine and curFace:
                    terminateClusters()
                    cv.terminate(curFace)
                curFace = cv.node("face")
                col = None
                primecol = None
                lln = 0
                curFaceValue = (
                    lineData["label"]["surface"].lower() if isFaceLine else "obverse"
                )
                if debug:
                    info(f"@{curFaceValue}")
                cv.feature(curFace, face=curFaceValue)
                if isFaceLine:
                    continue

            if lineType == "ColumnAtLine":
                col = lineData["label"]["column"]
                primeInfo = lineData["label"]["status"]
                primecol = len(primeInfo) > 0 and "PRIME" in primeInfo
                primecolAtt = dict(primecol=1) if primecol else {}
                continue

            if lineType == "ControlLine":
                content = lineData["content"][0]["cleanValue"]
                if content.startswith("note:"):
                    lineData["content"][0]["cleanValue"] = content[5:].lstrip()
                    lineData["prefix"] = "#note: "
                    lineType = "NoteLine"
                if content.startswith("tr."):
                    content = content.split(".", 1)[1]
                    parts = content.split(" ", 1)
                    lan = parts[0]
                    if lan in languages:
                        content = parts[1] if len(parts[1]) > 1 else ""
                    else:
                        (lan, content) = content.split(":", 1)
                        lan = lan.split(".", 1)[0]
                        if lan not in languages:
                            error(f"Unknown language {lan}", stop=True)
                    lineData["content"][0]["cleanValue"] = content
                    lineType = "TranslationLine"
                    lineData["prefix"] = f"#tr.{lan}: "

            isEmptyLine = lineType == "EmptyLine"
            isTextLine = lineType == "TextLine"

            if isEmptyLine or isTextLine:
                lln += 1
                curLine = cv.node("line")
                cv.feature(curLine, lln=lln)

                if isEmptyLine:
                    curSlot = cv.slot()
                    cv.feature(curSlot, type="empty")
                    prevLine = curLine
                    if col is not None:
                        cv.feature(curLine, col=col, **primecolAtt)
                        colprime = "'" if primecol else ""
                        colno = f"{col}{colprime}"
                        lnno = f"!{colno}:{lln}"
                    cv.feature(curLine, lnno=lnno)
                else:
                    numberData = lineData["lineNumber"]
                    ln = numberData["number"]
                    primeln = numberData["hasPrime"]
                    primelnAtt = dict(primeln=1) if primeln else {}

                    cv.feature(curLine, ln=ln, **primelnAtt)
                    lnprime = "'" if primeln else ""
                    lnno = f"{ln}{lnprime}"
                    if col is not None:
                        cv.feature(curLine, col=col, **primecolAtt)
                        colprime = "'" if primecol else ""
                        colno = f"{col}{colprime}"
                        lnno = f"{colno}:{lnno}"
                    if debug:
                        info(f"{lnno}")
                    cv.feature(curLine, lnno=lnno)

                    lineContent = lineData["content"]

                    erasure = ""

                    lastWord = len(lineContent) - 1

                    for (w, wordData) in enumerate(lineContent):
                        contentType = wordData["type"]
                        if erasure and contentType != "Erasure":
                            curWord = cv.node("word")
                            cv.feature(
                                curWord,
                                type="mark",
                                atf=erasure,
                                sym=erasure,
                                after=" ",
                            )
                            curSign = cv.slot()
                            cv.feature(
                                curSign,
                                type="erasure",
                                atf=erasure,
                                sym=erasure,
                                after=" ",
                                **getClusters(),
                            )
                            cv.terminate(curWord)

                        atf = wordData["value"]
                        sym = wordData["cleanValue"]

                        if contentType == "Erasure":
                            erasure += wordData["value"]
                        else:
                            curWord = cv.node("word")
                            after = "\n" if lastWord == w else " "
                            textAtts = dict(atf=atf, sym=sym, after=after)
                            cv.feature(curWord, **textAtts)

                            if contentType in {"Word", "LoneDeterminative"}:
                                lemmaData = wordData["uniqueLemma"]
                                lemma = ", ".join(lemmaData)
                                atts = {} if lang is None else dict(lang=lang)
                                cv.feature(curWord, type="word", **atts, lemma=lemma)

                                parts = wordData["parts"]
                                lastSign = len(parts) - 1

                                for (i, signData) in enumerate(parts):
                                    signType = signData["type"]
                                    isDeterminative = signType == "Determinative"
                                    isVariant = signType == "Variant"

                                    if isDeterminative or isVariant:
                                        subParts = signData[
                                            "tokens" if isVariant else "parts"
                                        ]
                                        lastSubPart = len(subParts) - 1

                                        if isDeterminative:
                                            doCluster(signData, "det", on=True)

                                        for (j, subPartData) in enumerate(subParts):
                                            after = (
                                                " "
                                                if lastSign == i and lastSubPart == j
                                                else ""
                                            )
                                            atts = (
                                                dict(variant=j + 1) if isVariant else {}
                                            )
                                            doSign(subPartData, after=after, **atts)

                                        if isDeterminative:
                                            doCluster(signData, "det", on=False)

                                    else:
                                        after = " " if lastSign == i else ""
                                        doSign(signData, after=after)

                            elif contentType == "Divider":
                                cv.feature(curWord, type="divider")
                                curSign = cv.slot()
                                cv.feature(curSign, type="divider", **textAtts)

                            elif contentType == "LanguageShift":
                                lang = wordData["cleanValue"][1:]
                                if lang == "akk":
                                    lang = None
                                cv.feature(curWord, type="lang")
                                curSign = cv.slot()
                                cv.feature(curSign, type="lang", **textAtts)

                            else:
                                cv.feature(curWord, type="mark")
                                curSign = cv.slot()
                                cv.feature(curSign, type="mark", **textAtts)

                                if contentType in {
                                    "BrokenAway",
                                    "Divider",
                                    "DocumentOrientedGloss",
                                }:
                                    doCluster(wordData, clusterType[contentType])
                                elif contentType == "ValueToken":
                                    error(f"unexpected word type {contentType}")

                                else:
                                    error(f"unrecognized word type {contentType}")

                            cv.terminate(curWord)

                    if erasure:
                        curWord = cv.node("word")
                        cv.feature(curWord, type="mark", atf=erasure)
                        curSign = cv.slot()
                        cv.feature(
                            curSign,
                            type="erasure",
                            atf=erasure,
                            sym=erasure,
                            after=after,
                        )
                        cv.terminate(curWord)

                prevLine = curLine

            else:
                if lineType == "ControlLine":
                    error(f"Unknown ControlLine: {atf[0:40]}")
                    continue

                content = " ".join(c["cleanValue"] for c in lineData["content"])
                if not content:
                    continue

                contents = {}

                if lineType == "RulingDollarLine":
                    tp = "ruling"

                elif lineType == "DiscourseAtLine":
                    tp = "colofon"

                elif lineType == "NoteLine":
                    tp = "note"

                elif lineType == "TranslationLine":
                    content = TRANS_RE.sub(r"\1", content)
                    if not content:
                        continue

                    parts = lineData["prefix"][1:].split(":", 1)[0].split(".")
                    lan = parts[1]
                    if lan not in languages:
                        error(f"Unknown language {lan}", stop=True)
                    else:
                        tp = f"tr@{lan}"
                        if len(parts) > 2 and parts[2]:
                            content = f"{parts[2]}:{content}"
                        contents["trans"] = 1

                elif lineType == "LooseDollarLine":
                    tp = "comment"

                elif lineType == "SealDollarLine":
                    tp = "seal"

                orig = cv.get(prevLine, tp)
                content = content if not orig else f"{orig}\n{content}"
                contents[tp] = content
                cv.feature(prevLine, **contents)

            cv.terminate(curLine)

        if curFace:
            terminateClusters()
            cv.terminate(curFace)
        cv.terminate(curDoc)

    # delete meta data of unused features

    for feat in featureMeta:
        if not cv.occurs(feat):
            error(f"feature {feat} does not occur")
            cv.meta(feat)


# TF LOADING (to test the generated TF)


def loadTf():
    TF = Fabric(locations=[OUT_DIR])
    allFeatures = TF.explore(silent=True, show=True)
    loadableFeatures = allFeatures["nodes"] + allFeatures["edges"]
    api = TF.load(loadableFeatures, silent=False)
    if api:
        print(f"max node = {api.F.otype.maxNode}")
        print("Frequency of readings")
        print(api.F.reading.freqList()[0:20])
        print("Frequency of grapheme")
        print(api.F.grapheme.freqList()[0:20])


# MAIN

command = None if len(sys.argv) <= 1 else sys.argv[1]

print(f"JSON to TF converter for {REPO}")
print(f"ATF source version = {VERSION_SRC}")
print(f"TF  target version = {VERSION_TF}")

if command is None:
    generateTf = True
    good = convert()
    if good:
        loadTf()
elif command == "-skipload":
    generateTf = True
    convert()
elif command == "-skipgen":
    loadTf()
else:
    print(f"Wrong command {command} !\n{HELP}")

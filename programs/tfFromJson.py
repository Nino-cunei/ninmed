import sys
import os
import re
import json
import yaml
from shutil import rmtree

from tf.fabric import Fabric
from tf.convert.walker import CV


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
    PERHAPS="uncertain",
    PERHAPS_BROKEN_AWAY="perhapsuncertain",
    BROKEN_AWAY="missing",
    DOCUMENT_ORIENTED_GLOSS="gloss",
    REMOVAL="excised",
    ACCIDENTAL_OMISSION="supplied",
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
    "fmt:text-orig-full": "{atfpre}{atf}{atfpost}{after}",
    "fmt:text-orig-plain": "{sym}{after}",
    "sectionFeatures": "pnumber,face,lnno",
    "sectionTypes": "document,face,line",
}

intFeatures = (
    set(
        """
        ln
        lln
        col
        langalt
        mark
        primeln
        primecol
        repeat
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
    "atfpost": {"description": "atf of cluster closings at sign"},
    "atfpre": {"description": "atf of cluster openings at sign"},
    "col": {"description": "ATF column number"},
    "collated": {"description": "whether a sign is collated (*)"},
    "collection": {"description": 'collection name from metadata field "collection"'},
    "comment": {
        "description": "$ comment to line or inline comment to slot ($ and $)",
    },
    "damage": {"description": "whether a sign is damaged"},
    "description": {"description": 'description from metadata field "description"'},
    "det": {
        "description": "whether a sign is a determinative gloss - between { }",
    },
    "docnote": {"description": "additional remarks in the document identification"},
    "docnumber": {"description": 'document number from metadata field "number"'},
    "excised": {
        "description": "whether a sign is excised - between << >>",
    },
    "face": {"description": "full name of a face including the enclosing object"},
    "flags": {"description": "sequence of flags after a sign"},
    "fraction": {"description": "fraction of a numeral"},
    "grapheme": {"description": "grapheme of a sign"},
    "lang": {"description": "language of a document"},
    "langalt": {
        "description": "1 if a sign is in the alternate language (i.e. Sumerian)"
    },
    "lemma": {
        "description": (
            "lemma of a word:"
            "comma-separated values of the uniqueLemma field in the JSON source"
        )
    },
    "lln": {"description": "logical line number of a numbered line"},
    "ln": {"description": "ATF line number of a numbered line, without prime"},
    "lnc": {"description": "ATF line identification of a comment line ($)"},
    "lnno": {
        "description": (
            "ATF line number, may be $ or #, with prime; column number prepended"
        ),
    },
    "mark": {"description": "whether a word is just an isolated mark"},
    "missing": {
        "description": "whether a sign is missing - between [ ]",
    },
    "operator": {"description": "the ! or x in a !() or x() construction"},
    "pnumber": {"description": "P number of a document"},
    "primecol": {"description": "whether a prime is present on a column number"},
    "primeln": {"description": "whether a prime is present on a line number"},
    "publication": {
        "description": 'publication info from metadata field "publication"'
    },
    "question": {"description": "whether a sign has the question flag (?)"},
    "reading": {"description": "reading of a sign"},
    "remarks": {"description": "# comment to line"},
    "remarkable": {"description": "whether a sign is remarkable (!)"},
    "repeat": {
        "description": (
            "repeat of a numeral; the value n (unknown) is represented as -1"
        ),
    },
    "sym": {"description": "essential part of a sign or of a word"},
    "supplied": {
        "description": "whether a sign is supplied - between < >",
    },
    "trans": {"description": "whether a line has a translation"},
    "translation@en": {"description": "translation of line in language en = English"},
    "type": {"description": "name of a type of cluster or kind of sign"},
    "variant": {"description": (
        "if sign is part of a variant pair, "
        "this is the sequence number of the variant (1 or 2)"
    )},
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
    curClusters = dict(
        supplied=None,
    )

    def terminateClusters():
        for tp in curClusters:
            node = curClusters[tp]
            if node:
                cv.terminate(node)
                curClusters[tp] = None

    def doCluster(cluster):
        cv.feature(curSign, type="mark")
        if signData["side"] == "LEFT":
            clusterNode = cv.node("cluster")
            curClusters[cluster] = clusterNode
            cv.feature(clusterNode, type=cluster)
        else:
            clusterNode = curClusters[cluster]
            if clusterNode:
                cv.terminate(clusterNode)

    def doSign(signData, **features):
        nonlocal curSign

        atf = signData["value"]
        curSign = cv.slot()
        clusterValues = {
            cluster: 1
            for (cluster, node) in curClusters.items()
            if node
        }
        cv.feature(curSign, atf=atf, **clusterValues, **features)
        signType = signData["type"]

        if signType == "AccidentalOmission":
            doCluster("supplied")
        elif signType == "Variant":
            print(f"WARNING: Nested Variant Signs {'X' * 50}")
        elif signType == "Removal":
            doCluster("excised")
        elif signType == "BrokenAway":
            doCluster("missing")
        elif signType == "Reading":
            sym = signData["name"]
            cv.feature(curSign, type="reading", sym=sym)
            pass
        elif signType == "Joiner":
            pass
        elif signType == "PerhapsBrokenAway":
            pass
        elif signType == "UnidentifiedSign":
            pass
        elif signType == "Determinative":
            pass
        elif signType == "Number":
            pass
        elif signType == "Logogram":
            pass
        elif signType == "UnknownNumberOfSigns":
            pass
        elif signType == "UnclearSign":
            pass

    paths = getJsonFiles()
    for (i, path) in enumerate(paths):
        fileName = path.split("/")[-1].rsplit(".", 1)[0]
        data = readJsonFile(path)
        metaData = {}
        for (origField, (field, tp)) in META_FIELDS.items():
            origFields = origField.split(".", 1)
            metaData[field] = (
                data[origField]
                if len(origFields) == 1
                else data[origFields[0]][origFields[1]]
            )
        textData = data["text"]["allLines"]
        nLines = len(textData)

        print(f"{i + 1:>3} {nLines:>4} lines in {fileName}")
        if nLines == 0:
            continue

        curDoc = cv.node("document")
        cv.feature(curDoc, **metaData)
        curFace = None
        col = None
        primecol = None
        lln = 0

        for lineData in textData:
            lineType = lineData["type"]
            isFaceLine = lineType == "SurfaceAtLine"

            if isFaceLine or not curFace:
                if isFaceLine and curFace:
                    terminateClusters()
                    cv.terminate(curFace)
                curFace = cv.node("face")
                col = None
                primecol = None
                lln = 0
                face = lineData["label"]["surface"].lower() if isFaceLine else "obverse"
                cv.feature(curFace, face=face)
                if isFaceLine:
                    continue

            if lineType == "ColumnAtLine":
                col = lineData["label"]["column"]
                primeInfo = lineData["label"]["status"]
                primecol = len(primeInfo) > 0 and "PRIME" in primeInfo
                continue

            lln += 1
            curLine = cv.node("line")
            cv.feature(curLine, lln=lln)

            if lineType == "EmptyLine":
                curSlot = cv.slot()
                cv.feature(curSlot, type="empty")

            elif lineType == "TextLine":
                numberData = lineData["lineNumber"]
                ln = numberData["number"]
                primeln = numberData["hasPrime"]

                cv.feature(curLine, ln=ln, primeln=primeln)
                lnprime = "'" if primeln else ""
                lnno = f"{ln}{lnprime}"
                if col is not None:
                    cv.feature(curLine, col=col, primecol=primecol)
                    colprime = "'" if primecol else ""
                    lnno = f"{colprime}:{lnprime}"
                cv.feature(curLine, lnno=lnno)

                lineContent = lineData["content"]

                erasure = ""

                for contentData in lineContent:
                    contentType = contentData["type"]
                    if erasure and contentType != "Erasure":
                        curWord = cv.node("word")
                        cv.feature(curWord, mark=1, atf=erasure)
                        curSign = cv.slot()
                        clusterValues = {
                            cluster: 1
                            for (cluster, node) in curClusters.items()
                            if node
                        }
                        cv.feature(
                            curSign, type="erasure", atf=erasure, **clusterValues
                        )
                        cv.terminate(curWord)

                    atf = contentData["value"]

                    if contentType == "Erasure":
                        erasure += contentData["value"]
                    else:
                        curWord = cv.node("word")
                        cv.feature(curWord, atf=atf, after=" ")

                        if contentType == "Word":
                            langalt = contentData["language"] == "SUMERIAN"
                            lemmaData = contentData["uniqueLemma"]
                            lemma = ", ".join(lemmaData)
                            cv.feature(curWord, langalt=langalt, lemma=lemma)

                            for signData in contentData["parts"]:
                                signType = signData["type"]

                                if signType == "Variant":
                                    for (i, tokenData) in enumerate(signData["tokens"]):
                                        doSign(tokenData, variant=i + 1)
                                else:
                                    doSign(signData)
                        else:
                            cv.feature(curWord, mark=1)
                            curSign = cv.slot()
                            cv.feature(curSign, type="mark", atf=atf)

                            if contentType == "BrokenAway":
                                pass
                            elif contentType == "ValueToken":
                                pass

                            elif contentType == "Divider":
                                pass

                            elif contentType == "DocumentOrientedGloss":
                                pass

                            elif contentType == "LanguageShift":
                                pass

                            elif contentType == "LoneDeterminative":
                                pass

                        cv.terminate(curWord)

                if erasure:
                    curWord = cv.node("word")
                    cv.feature(curWord, mark=1, atf=erasure)
                    curSign = cv.slot()
                    cv.feature(curSign, type="erasure", atf=erasure)
                    cv.terminate(curWord)

            else:
                if lineType == "RulingDollarLine":
                    atf = lineData["displayValue"]
                    tp = "ruling"

                elif lineType == "ControlLine":
                    atf = "\n".join(c["value"] for c in lineData["content"])
                    tp = "control"

                elif lineType == "TranslationLine":
                    atf = "\n".join(c["value"] for c in lineData["content"])
                    atf = TRANS_RE.sub(r"\1", atf)
                    tp = "translation"

                elif lineType == "DiscourseAtLine":
                    atf = lineData["displayValue"]
                    tp = "colofon"

                elif lineType == "NoteLine":
                    atf = "\n".join(c["value"] for c in lineData["content"])
                    tp = "note"

                elif lineType == "LooseDollarLine":
                    atf = lineData["displayValue"]
                    tp = "comment"

                elif lineType == "SealDollarLine":
                    atf = lineData["displayValue"]
                    tp = "seal"

                cv.feature(curLine, type=tp, atf=atf)
                curSlot = cv.slot()
                cv.feature(curSlot, type="empty")

            cv.terminate(curLine)

        if curFace:
            terminateClusters()
            cv.terminate(curFace)
        cv.terminate(curDoc)

    # delete meta data of unused features

    for feat in featureMeta:
        if not cv.occurs(feat):
            print(f"WARNING: feature {feat} does not occur")
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

generateTf = len(sys.argv) == 1 or sys.argv[1] != "-notf"

print(f"JSON to TF converter for {REPO}")
print(f"ATF source version = {VERSION_SRC}")
print(f"TF  target version = {VERSION_TF}")
good = convert()

if generateTf and good:
    loadTf()

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
python3 tfFromJson.py -Pnumber
python3 tfFromJson.py -Pnumber:obverse
python3 tfFromJson.py -Pnumber:obverse:2:1
    Generate TF, only this Pnumber, face, line, do not load it
    Primes in numbers are not relevant
python3 tfFromJson.py -skipgen
    Load TF
python3 tfFromJson.py -skipload
    Generate TF but do not load it
"""

TEST = """
P365742-K.2354: 63.: [x x x x {ši]m}LI GAZ KI ZI₃.KUM HI.HI ina A GAZI{sar} SILA₁₁-aš LAL IGI GIG tu-gal-lab EN TI.LA LAL₂
P394523-K.2573: 17'.: [ina A.M]E[Š? ... UKU]Š₂.LAGAB U₂-BABBAR x [... t]e-qi₂?#
P394520-K.2570: 9'.: [DIŠ NA IGI.MIN-šu₂ GIG? ... {u₂}EME.U]R.GI₇ {u₂}IN₆.UŠ ina ZI₃.KUM HE.HE ina GEŠTIN N[A]G?
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

clusterSpecs = (
    ("BrokenAway", "missing", "[", "]", None),
    ("PerhapsBrokenAway", "uncertain", "(", ")", None),
    ("Removal", "excised", "<<", ">>", None),
    ("AccidentalOmission", "supplied", "<", ">", None),
    ("DocumentOrientedGloss", "gloss", "{(", ")}", None),
    ("Determinative", "det", "{", "}", None),
    ("LoneDeterminative", "det", "{", "}", None),
    ("Erasure", "erasure", "°", "°", "\\"),
)

clusterType = {x[0]: x[1] for x in clusterSpecs}
clusterChar = {x[1]: {True: x[2], False: x[3], None: x[4]} for x in clusterSpecs}

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
    "atf": {"description": "full atf of a sign"},
    "atfpost": {"description": "cluster characters that follow a sign or word"},
    "atfpre": {"description": "cluster characters that precede a sign or word"},
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
    "erasure": {
        "description": (
            "whether a sign is in an erasure - between ° \\ °: "
            "1: between ° and \\; 2: between \\ and °"
        ),
    },
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
    "museum": {"description": 'museum name from metadata field "museum.name"'},
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
    "uncertain": {"description": "whether a sign is uncertain - between ( )"},
    "variant": {
        "description": (
            "if sign is part of a variant pair, "
            "this is the sequence number of the variant (1 or 2)"
        )
    },
}


def msg(m):
    sys.stdout.write(f"{m}\n")


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


PNUMBER = None
FACE = None
LINE = None


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
    DEBUG = False
    curClusters = {cluster: (None, 0) for cluster in clusterType.values()}

    def debug(m):
        if DEBUG:
            msg(f"INFO  ======> {m}")
            sys.stdout.flush()

    def error(m, stop=False):
        msg(f"ERROR ======> {m}")
        sys.stdout.flush()
        if stop:
            quit()

    def terminateClusters():
        for tp in curClusters:
            (node, val) = curClusters[tp]
            if node:
                cv.terminate(node)
                curClusters[tp] = (None, 0)

    def doCluster(data, cluster, on=None, off=None):
        makeOn = data["side"] == "LEFT" if on is None else on
        makeOff = data["side"] == "RIGHT" if off is None else off
        makeAlt = data["side"] == "CENTER" if off is None and on is None else off and on
        status = True if makeOn else False if makeOff else None
        if status is None and not makeAlt:
            error(f"cluster {cluster} not on and not off and not alt", stop=True)

        (clusterNode, clusterVal) = curClusters[cluster]
        if status is True:
            if clusterNode is not None:
                error(f"cluster {cluster} is nesting", stop=True)
            clusterNode = cv.node("cluster")
            curClusters[cluster] = (clusterNode, 1)
            cv.feature(clusterNode, type=cluster)
        elif status is False:
            if clusterNode is None:
                error(f"cluster {cluster} is spuriously closed", stop=True)
            else:
                cv.terminate(clusterNode)
                curClusters[cluster] = (None, 0)
        elif status is None:
            if clusterNode is None or clusterVal == 0:
                error(f"cluster {cluster} is missing first part", stop=True)
            elif clusterVal > 1:
                error(f"cluster {cluster} has too many parts", stop=True)
            else:
                curClusters[cluster] = (clusterNode, 2)
        return status

    def getClusters():
        return {
            cluster: val
            for (cluster, (node, val)) in curClusters.items()
            if node is not None
        }

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

    def doSign(data, wordAfter, isLast, **features):
        nonlocal curSign
        nonlocal nextPre
        nonlocal lang

        signType = data["type"]
        after = wordAfter if isLast else ""

        if signType in {
            "AccidentalOmission",
            "Erasure",
            "Removal",
            "BrokenAway",
            "PerhapsBrokenAway",
            "DocumentOrientedGloss",
        }:
            cluster = clusterType[signType]
            status = doCluster(data, cluster)
            if status is True:
                nextPre += clusterChar[cluster][status]
            elif status is False:
                cv.feature(
                    curSign,
                    after=(cv.get("after", curSign) or "") + after,
                    atfpost=(cv.get("atfpost", curSign) or "")
                    + clusterChar[cluster][status],
                )
            elif status is None:
                nextPre += clusterChar[cluster][status]

        elif signType == "LanguageShift":
            lang = data["cleanValue"][1:]
            nextPre += f"%{lang} "
            if lang == "akk":
                lang = None

        elif signType == "Joiner":
            if curSign is not None:
                cv.feature(curSign, after=data["value"])

        else:
            atf = data["value"]
            atfPre = ""
            atfPost = ""
            extraFlag = ""

            indexStart = atf.find("[")
            indexEnd = atf.find("]")

            startMissingInternal = atf != "[" and indexStart >= 0
            endMissingInternal = atf != "]" and indexEnd >= 0

            if startMissingInternal and endMissingInternal:
                if indexStart < indexEnd:
                    extraFlag = "#"
                    atf = atf.replace("[", "").replace("]", "") + extraFlag
                else:
                    atf = atf.replace("[", "").replace("]", "")
            elif startMissingInternal:
                atf = atf.replace("[", "")
                atfPre = "["
                doCluster(data, "missing", on=True, off=False)

            curSign = cv.slot()

            if endMissingInternal and not startMissingInternal:
                atf = atf.replace("]", "")
                atfPost += "]"
                doCluster(data, "missing", on=False, off=True)

            thisPre = nextPre + atfPre
            atfPreFeat = dict(atfpre=thisPre) if thisPre else {}
            atfPre = ""
            nextPre = ""
            atfPostFeat = dict(atfpost=atfPost) if atfPost else {}
            atfPost = ""

            cv.feature(
                curSign,
                **atfPreFeat,
                **atfPostFeat,
                atf=atf,
                **getClusters(),
                **features,
            )
            doFlags(data, curSign, extraFlag)
            doModifiers(data, curSign)

            sym = data["cleanValue"]
            feats = {}

            if signType == "UnknownNumberOfSigns":
                tp = "ellipsis"

            elif signType == "UnidentifiedSign":
                tp = "unknown"

            elif signType == "UnclearSign":
                tp = "unknown"

            elif signType == "Number":
                tp = "numeral"
                feats = dict(number=sym)

            elif signType == "Logogram":
                tp = "grapheme"
                feats = dict(grapheme=sym)

            elif signType == "Reading":
                tp = "reading"
                sign = data.get("sign", None)
                reading = data["name"]
                if sign is None:
                    feats = dict(reading=reading)
                else:
                    grapheme = sign["cleanValue"]
                    feats = dict(reading=reading, grapheme=grapheme)

            elif signType == "Joiner":
                tp = "joiner"

            elif signType == "Divider":
                tp = "wdiv"
                after = wordAfter

            elif signType == "Determinative" or signType == "Variant":
                error(f"nested {signType} Signs", stop=True)

            else:
                error(f"unrecognized sign type {signType}", stop=True)

            cv.feature(curSign, type=tp, after=after, sym=sym, **feats)

    paths = getJsonFiles()
    skipFace = FACE is not None
    skipLine = LINE is not None

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
        pNumber = metaData["pnumber"]
        if PNUMBER is not None and PNUMBER != pNumber:
            continue

        textData = docData["text"]["allLines"]
        nLines = len(textData)

        msg(f"{i + 1:>3} {nLines:>4} lines in {fileName}")
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
            content = " ".join(c["value"] for c in lineData["content"])
            atf = f"{lineData['prefix']} {content}"

            isFaceLine = lineType == "SurfaceAtLine"
            if isFaceLine:
                thisFaceValue = lineData["label"]["surface"].lower()
                if FACE is not None:
                    skipFace = thisFaceValue != FACE
                if thisFaceValue == curFaceValue:
                    continue

            if skipFace:
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
                cv.feature(curFace, face=curFaceValue)
                if isFaceLine:
                    debug(atf)
                    continue

            if lineType == "ColumnAtLine":
                col = lineData["label"]["column"]
                primeInfo = lineData["label"]["status"]
                primecol = len(primeInfo) > 0 and "PRIME" in primeInfo
                primecolAtt = dict(primecol=1) if primecol else {}
                debug(atf)
                continue

            if lineType == "ControlLine":
                content = lineData["content"][0]["value"]
                if content.startswith("note:"):
                    lineData["content"][0]["value"] = content[5:].lstrip()
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
                    lineData["content"][0]["value"] = content
                    lineType = "TranslationLine"
                    lineData["prefix"] = f"#tr.{lan}: "

            isEmptyLine = lineType == "EmptyLine"
            isTextLine = lineType == "TextLine"

            if isEmptyLine or isTextLine:
                lln += 1
                curLine = cv.node("line")
                cv.feature(curLine, lln=lln, atf=atf)

                if isEmptyLine:
                    if not skipLine:
                        debug(atf)
                    curSlot = cv.slot()
                    cv.feature(curSlot, type="empty")
                    prevLine = curLine
                    if col is None:
                        lnno = f"!{lln}"
                    else:
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

                    lnprime = "'" if primeln else ""
                    lnno = f"{ln}{lnprime}"

                    if col is not None:
                        cv.feature(curLine, col=col, **primecolAtt)
                        colprime = "'" if primecol else ""
                        colno = f"{col}{colprime}"
                        lnno = f"{colno}:{lnno}"

                    if LINE is not None:
                        skipLine = lnno.replace("'", "") != LINE

                    if skipLine:
                        continue

                    debug(atf)
                    cv.feature(curLine, ln=ln, **primelnAtt, lnno=lnno)

                    lineContent = lineData["content"]

                    lineSigns = []

                    for wordData in lineContent:
                        if "parts" in wordData:
                            lineSigns.append([True, wordData, False])
                            for signData in wordData["parts"]:
                                hasSubs = False
                                for (kind, tp) in (
                                    ("parts", "Determinative"),
                                    ("tokens", "Variant"),
                                ):
                                    if kind in signData:
                                        hasSubs = True
                                        end = len(signData[kind])
                                        for (i, subPart) in enumerate(signData[kind]):
                                            lineSigns.append(
                                                [
                                                    False,
                                                    subPart,
                                                    False,
                                                    tp,
                                                    i,
                                                    i == end - 1,
                                                ]
                                            )
                                if not hasSubs:
                                    lineSigns.append([False, signData, False])
                        else:
                            lineSigns.append([None, wordData, None])

                    for entry in reversed(lineSigns):
                        isWord = entry[0]
                        if isWord:
                            entry[2] = True
                            break

                    atWordEnd = True
                    for entry in reversed(lineSigns):
                        isWord = entry[0]
                        if isWord is False:
                            if atWordEnd:
                                entry[2] = True
                                atWordEnd = False
                        elif isWord is True:
                            atWordEnd = True

                    curWord = None
                    curSign = None
                    nextPre = ""

                    for (e, entry) in enumerate(lineSigns):
                        isWord = entry[0]
                        data = entry[1]
                        isLast = entry[2]
                        where = None if len(entry) < 4 else entry[3]
                        contentType = data["type"]
                        if isWord:
                            if curWord:
                                cv.terminate(curWord)
                            atf = data["value"]
                            sym = data["cleanValue"]
                            curWord = cv.node("word")
                            wordAfter = "\n" if isLast else " "
                            cv.feature(curWord, atf=atf, sym=sym, after=wordAfter)

                            if contentType in {"Word", "LoneDeterminative"}:
                                lemmaData = data["uniqueLemma"]
                                lemma = ", ".join(lemmaData)
                                atts = {} if lang is None else dict(lang=lang)
                                cv.feature(curWord, type="word", **atts, lemma=lemma)

                        elif isWord is False:
                            if len(entry) > 3:
                                tp = entry[3]
                                where = entry[4]
                                atEnd = entry[5]
                                atts = {}
                                if tp == "Determinative":
                                    if where == 0:
                                        doCluster(data, "det", on=True, off=False)
                                        nextPre += "{"
                                    doSign(data, wordAfter, isLast)
                                    if atEnd:
                                        cv.feature(
                                            curSign,
                                            atfpost=(cv.get("atfpost", curSign) or "")
                                            + "}",
                                        )
                                        doCluster(data, "det", on=False, off=True)
                                elif tp == "Variant":
                                    doSign(data, wordAfter, isLast, variant=where + 1)
                                    if not atEnd:
                                        cv.feature(
                                            curSign,
                                            atfpost=(cv.get("atfpost", curSign) or "")
                                            + "/",
                                        )
                                else:
                                    error(f"Unknown complex type: {tp}", stop=True)
                            else:
                                doSign(data, wordAfter, isLast)
                        else:
                            doSign(data, " ", isLast)

                    if nextPre != "":
                        error(
                            f"dangling pre material at last sign of line: {nextPre}",
                            stop=True,
                        )

                    cv.terminate(curWord)

                prevLine = curLine
                cv.terminate(curLine)

            else:
                if skipLine:
                    continue

                debug(atf)

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

                orig = cv.get(tp, prevLine)
                content = content if not orig else f"{orig}\n{content}"
                contents[tp] = content
                cv.feature(prevLine, **contents)

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
        msg(f"max node = {api.F.otype.maxNode}")
        msg("Frequency of readings")
        msg(api.F.reading.freqList()[0:20])
        msg("Frequency of grapheme")
        msg(api.F.grapheme.freqList()[0:20])


# MAIN

command = None if len(sys.argv) <= 1 else sys.argv[1]

msg(f"JSON to TF converter for {REPO}")
msg(f"ATF source version = {VERSION_SRC}")
msg(f"TF  target version = {VERSION_TF}")

if command is None:
    generateTf = True
    good = convert()
    if good:
        loadTf()
elif command.startswith("P"):
    generateTf = True
    parts = command.split(":", 1)
    PNUMBER = parts[0]
    if len(parts) > 1:
        parts = parts[1].split(":", 1)
        FACE = parts[0]
        if len(parts) > 1:
            LINE = parts[1].replace("'", "")
    convert()
elif command == "-skipload":
    generateTf = True
    convert()
elif command == "-skipgen":
    loadTf()
else:
    msg(f"Wrong command {command} !\n{HELP}")

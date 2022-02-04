import collections
import os
import json
import yaml


def readYaml(fileName):
    if os.path.exists(fileName):
        with open(fileName) as y:
            y = yaml.load(y, Loader=yaml.FullLoader)
    else:
        y = {}
    return y


GH = os.path.expanduser("~/github")
ORG = "Nino-cunei"
REPO = "ninmed"
REPO_DIR = f"{GH}/{ORG}/{REPO}"
REPORT_DIR = f"{REPO_DIR}/report"
DECL_PATH = f"{REPO_DIR}/yaml"
META_DECL_FILE = f"{DECL_PATH}/meta.yaml"

META_DECL = readYaml(META_DECL_FILE)

VERSION_SRC = META_DECL["versionSrc"]
VERSION_TF = META_DECL["versionTf"]
SRC_DIR = f"{REPO_DIR}/source/json/{VERSION_SRC}"

SKIP_KEYS = set(
    """
accession
bmIdNumber
folios
joins
measures
record
references
script
""".strip().split()
)


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

    walk(SRC_DIR)
    return sorted(filePaths)


def readJsonFile(path):
    with open(path) as fh:
        data = json.load(fh)
    return data


def writeReport(fName, lines):
    with open(f"{REPORT_DIR}/{fName}", "w") as fh:
        for line in lines:
            fh.write(f"{line}\n")


def investigate(data):
    entries = []

    def walk(path, info):
        if type(info) is dict:
            for (k, v) in sorted(info.items()):
                pathRep = f"{path}." if path else ""
                walk(f"{pathRep}{k}", v)
        elif type(info) is list:
            for v in info:
                pathRep = f"{path}[]" if path else ""
                walk(f"{pathRep}", v)
        else:
            entries.append((path, info))

    walk("", data)
    return entries


def filter(data, include=None, exclude=set()):
    filtered = []

    def walk(path, info):
        if path in exclude:
            return
        if type(info) is dict:
            for (k, v) in sorted(info.items()):
                pathRep = f"{path}." if path else ""
                walk(f"{pathRep}{k}", v)
        elif type(info) is list:
            for (k, v) in enumerate(info):
                pathRep = f"{path}[{k}]" if path else ""
                walk(f"{pathRep}", v)
        else:
            if type(info) is str:
                nInfo = len(info)
                if nInfo > 20:
                    info = info[0:20].replace("\n", " ") + "..."
            filtered.append((path, info))

    if include is None:
        walk("", data)
    else:
        walk("", data.get(include, {}))
    return filtered


def compact(path, doMeta=False, doText=False):
    data = readJsonFile(path)
    pNum = data["cdliNumber"]
    meta = filter(data, exclude={"text"}) if doMeta else []
    meta = "\n".join(f"{path:<40} = {val}" for (path, val) in meta)
    text = filter(data, include="text") if doText else []
    textRep = []
    for (path, val) in text:
        path = (
            path.replace("allLines", "a")
            .replace("content", "c")
            .replace("parts", "p")
            .replace("nameParts", "n")
            .replace("lineNumber", "l")
        )
        textRep.append(f"{path:<20} = {val}")
    text = "\n".join(textRep)
    print(f"{pNum}\n{meta}\n{text}")


def analyse(data, theKey, instead=None, asData=False, full=False):
    entries = collections.defaultdict(set)
    if instead is not None:
        (theValue, otherKey) = instead[0:2]
        subKey = instead[2] if len(instead) >= 2 else None

    def walk(path, info, parent):
        if not full and path in SKIP_KEYS:
            return
        if path == theKey or path.endswith(f".{theKey}") or path.endswith(f"]{theKey}"):
            if instead is None:
                entries[path].add(repr(info))
            else:
                if info == theValue:
                    lookup = parent[otherKey]
                    if subKey is not None:
                        lookup = (
                            tuple(c[subKey] for c in lookup)
                            if type(lookup) is list
                            else lookup[subKey]
                        )

                    entries[path].add(lookup)
        elif type(info) is dict:
            for (k, v) in sorted(info.items()):
                pathRep = f"{path}." if path else ""
                walk(f"{pathRep}{k}", v, info)
        elif type(info) is list:
            for v in info:
                pathRep = f"{path}[]" if path else ""
                walk(f"{pathRep}", v, info)

    walk("", data, {})
    if asData == 1:
        return entries
    lines = []
    for (path, types) in sorted(entries.items(), key=lambda x: x[0]):
        if asData:
            lines.append(path)
            for tp in types:
                lines.append((f"\t{tp}"))
        else:
            print(path)
            for tp in types:
                print(f"\t{tp}")
    if asData:
        return lines


def analyseAll(theKey, instead=None, asData=False, toFile=True, full=False):
    data = []
    for path in getJsonFiles():
        data.append(readJsonFile(path))
    lines = analyse(data, theKey, instead=instead, asData=True, full=full)
    if asData:
        return lines
    elif toFile:
        base = theKey if instead is None else f"{theKey}-{instead[0]}-{instead[1]}"
        writeReport(f"{base}.txt", lines)
    else:
        print("\n".join(lines))


def output(items, toFile, fileName):
    lines = []
    for (item, docNums) in items.items():
        lines.append(item)
        for docNum in docNums:
            lines.append(f"\t{docNum}")
    if toFile:
        writeReport(fileName, lines)
    else:
        print("\n".join(lines))


def getData():
    for path in getJsonFiles():
        data = readJsonFile(path)
        docNum = data["number"]
        yield (docNum, data)


def getFaces(toFile=True):
    fileName = "faces.txt"
    items = collections.defaultdict(list)
    for (docNum, data) in getData():
        for lineData in data["text"]["allLines"]:
            if lineData["type"] != "SurfaceAtLine":
                continue
            value = lineData["displayValue"]
            items[value].append(docNum)
    output(items, toFile, fileName)


def getColumns(toFile=True):
    fileName = "columns.txt"
    items = collections.defaultdict(list)
    for (docNum, data) in getData():
        for lineData in data["text"]["allLines"]:
            if lineData["type"] != "ColumnAtLine":
                continue
            value = lineData["displayValue"]
            items[value].append(docNum)
    output(items, toFile, fileName)


def getContentTypes(toFile=True):
    fileName = "contenttypes.txt"
    items = collections.defaultdict(set)
    for (docNum, data) in getData():
        for lineData in data["text"]["allLines"]:
            for contentData in lineData["content"]:
                contentType = contentData["type"]
                items[contentType].add(docNum)
    output(items, toFile, fileName)


def getVariants(toFile=True):
    fileName = "variants.txt"
    items = collections.defaultdict(set)
    for (docNum, data) in getData():
        for lineData in data["text"]["allLines"]:
            for contentData in lineData["content"]:
                contentType = contentData["type"]
                if contentType == "Word":
                    for signData in contentData["parts"]:
                        signType = signData["type"]
                        if signType == "Variant":
                            variant = signData["value"]
                            items[variant].add(docNum)
    output(items, toFile, fileName)


META_KEYS = {
    "collection": "collection",
    "description": "description",
    "museum.name": "museum",
    "number": "xnum",
    "publication": "published",
}

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


def getLine(line):
    prefix = line["prefix"]
    content = " ".join(c["value"] for c in line.get("content", []))
    return (prefix, content)


def extractLines(path, asData=False):
    data = readJsonFile(path)
    pNum = data["cdliNumber"]
    xNum = data["number"]

    result = [f"@pnum={pNum}", f"@xnum={xNum}"]

    lines = data["text"]["allLines"]

    for line in lines:
        (prefix, content) = getLine(line)
        result.append(f"{pNum}-{xNum}: {prefix}: {content}")

    if asData:
        return result
    print("\n".join(result))


def extractAllLines():
    lines = []
    for path in getJsonFiles():
        lines.extend(extractLines(path, asData=True))
    writeReport("all-lines.txt", lines)


def extract(path):
    data = readJsonFile(path)
    pNum = data["cdliNumber"]
    meta = filter(data, exclude={"text"})

    result = [f"@pnum={pNum}"]

    for (path, val) in meta:
        meta = META_KEYS.get(path, None)
        if meta:
            result.append(f".{meta}={val}")

    lines = data["text"]["allLines"]
    for line in lines:
        tp = line["type"]
        prefix = line["prefix"]
        result.append(f"*{tp}")
        result.append(prefix)

    print("\n".join(result))

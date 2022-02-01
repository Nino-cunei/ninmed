import collections
import os
import json


GH = os.path.expanduser("~/github")
ORG = "Nino-cunei"
REPO = "ninmed"
REPO_DIR = f"{GH}/{ORG}/{REPO}"
SRC_DIR = f"{REPO_DIR}/source/json"
REPORT_DIR = f"{REPO_DIR}/report"


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


def analyse(data, theKey):
    entries = collections.defaultdict(set)

    def walk(path, info):
        if path == theKey or path.endswith(f".{theKey}") or path.endswith(f"]{theKey}"):
            entries[path].add(repr(info))
        elif type(info) is dict:
            for (k, v) in sorted(info.items()):
                pathRep = f"{path}." if path else ""
                walk(f"{pathRep}{k}", v)
        elif type(info) is list:
            for v in info:
                pathRep = f"{path}[]" if path else ""
                walk(f"{pathRep}", v)
        else:
            if (
                path == theKey
                or path.endswith(f".{theKey}")
                or path.endswith(f"]{theKey}")
            ):
                entries[path].add(info)

    walk("", data)
    for (path, types) in sorted(entries.items(), key=lambda x: x[0]):
        print(path)
        for tp in types:
            print(f"\t{tp}")


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
    tp = line["type"]
    content = " ".join(c["value"] for c in line.get("content", []))
    if tp == "EmptyLine":
        prefix = ""
    elif tp == "TextLine":
        info = line.get("lineNumber", {})
        prefix = "" + (
            ";".join(
                (
                    str(info["number"]),
                    "'" if info["hasPrime"] else "",
                )
            )
        )
    elif tp == "ColumnAtLine":
        info = line["label"]
        prefix = "@column" + (
            ";".join(
                (
                    str(info["column"]),
                    "'" if info["status"] == ["PRIME"] else "",
                )
            )
        )
    elif tp == "DiscourseAtLine":
        prefix = "#colophon"
    elif tp == "SurfaceAtLine":
        info = line["label"]
        prefix = "@face" + (
            ";".join(
                (
                    info["abbreviation"],
                    "'" if info["status"] == ["PRIME"] else "",
                )
            )
        )
    elif tp == "ControlLine":
        (pre, content) = content.split(":", 1)
        preParts = pre.split(".", 1)
        kind = preParts[0]
        atts = preParts[1] if len(preParts) > 1 else ""
        attParts = atts.split(".", 1)
        lang = attParts[0]
        extra = attParts[1] if len(attParts) > 1 else ""
        prefix = f"#{kind};{lang};{extra}"
        if not kind.startswith("tr"):
            print(f"Strange ControlLine: {content}")
    elif tp == "NoteLine":
        prefix = "#note"
    elif tp == "TranslationLine":
        lang = line["language"]
        prefix = f"#tr;{lang};"
    elif tp == "LooseDollarLine":
        prefix = "$"
    elif tp == "RulingDollarLine":
        number = line["number"].lower()
        prefix = f"$ruling;{number}"
    elif tp == "SealDollarLine":
        prefix = "$seal"
    else:
        prefix = f"!!!{tp}"
        print(f"Unknown line type: {tp}")
    return (prefix, content)


def extractLines(path, asData=False):
    data = readJsonFile(path)
    pNum = data["cdliNumber"]

    result = [f"@pnum={pNum}"]

    lines = data["text"]["allLines"]

    for line in lines:
        (prefix, content) = getLine(line)
        tp = line["type"]
        result.append(f"{tp}: {prefix}: {content}")

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

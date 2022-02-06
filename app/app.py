import types
from tf.advanced.app import App


MODIFIERS = """
    collated
    remarkable
    question
    damage
    uncertain
    missing
    excised
    supplied
""".strip().split()


def fmt_layoutFull(app, n, **kwargs):
    return app._wrapHtml(n, "atf")


def fmt_layoutPlain(app, n, **kwargs):
    return app._wrapHtml(n, "sym")


class TfApp(App):
    def __init__(app, *args, **kwargs):
        app.fmt_layoutFull = types.MethodType(fmt_layoutFull, app)
        app.fmt_layoutPlain = types.MethodType(fmt_layoutPlain, app)
        super().__init__(*args, **kwargs)
        api = app.api
        Fall = api.Fall
        allNodeFeatures = set(Fall())
        app.modifiers = [m for m in MODIFIERS if m in allNodeFeatures]

    def _wrapHtml(app, n, kind):
        modifiers = app.modifiers
        api = app.api
        F = api.F
        Fs = api.Fs
        typ = F.type.v(n)
        after = F.after.v(n)
        if typ == "empty":
            material = '<span class="empty">∅</span>'
        elif typ == "unknown":
            part = F.sym.v(n) or ""
            if part:
                cls = "g" if part.isupper() else "r"
                if cls == "g":
                    partR = ""
                    partG = f'<span class="cls">{part}</span>'
                else:
                    partR = f'<span class="cls">{part}</span>'
                    partG = ""
            material = f'<span class="uncertain">{partR}{partG}</span>'
        elif typ == "ellipsis":
            material = f'<span class="missing">{F.sym.v(n)}</span>'
        elif typ == "reading":
            material = f'<span class="r">{F.reading.v(n)}</span>'
        elif typ == "grapheme":
            material = f'<span class="g">{F.grapheme.v(n)}</span>'
        elif typ == "numeral":
            material = Fs(kind).v(n)
        else:
            material = Fs(kind).v(n)
        clses = " ".join(cf for cf in modifiers if Fs(cf).v(n))
        if clses:
            material = f'<span class="{clses}">{material}</span>'
        if F.det.v(n):
            material = f'<span class="det">{material}</span>'
        if F.lang.v(n) and F.lang.v(n) != "akk":
            material = f'<span class="lang">{material}</span>'
        return f"{material}{after}"

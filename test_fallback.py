"""Test de uitwijk-keten van generate.py zonder Gemini aan te roepen.

Run #12 viel op 17 aug om een 503 die urenlang aanhield. De fix (uitwijken naar
een ander model) is nooit tegen een echte run getest — en op maandag 09:00 is
er geen tweede kans. Dit stubt de HTTP-laag, zodat elk faalpad hier afgaat in
plaats van in productie.

    python3 test_fallback.py
"""
import io, sys, urllib.error, urllib.request

sys.path.insert(0, ".")
from pipeline import generate as g

GOED = b'{"candidates":[{"content":{"parts":[{"text":"# Titel\\n\\nTekst."}]}}]}'


def _http(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://x", code, "boem", {},
        io.BytesIO(b'{"error":{"message":"This model is currently experiencing high demand"}}'))


class Stub:
    """Vervangt urlopen. antwoorden: model -> code of GOED."""

    def __init__(self, plan):
        self.plan = plan
        self.calls = []

    def __call__(self, req, timeout=None):
        model = req.full_url.split("/models/")[1].split(":")[0]
        self.calls.append(model)
        uitkomst = self.plan.get(model, 503)
        if uitkomst is GOED:
            class R:
                def read(self_inner): return GOED
                def __enter__(self_inner): return self_inner
                def __exit__(self_inner, *a): return False
            return R()
        raise _http(uitkomst)


def scenario(naam, plan, verwacht_model=None, verwacht_fout=None):
    stub = Stub(plan)
    g.urllib.request.urlopen = stub
    g.time.sleep = lambda s: None          # geen echte wachttijd in de test
    try:
        g._vraag_gemini(b"{}", "sleutel")
        gelukt, fout = True, ""
    except g.GeneratieFout as e:
        gelukt, fout = False, str(e)

    geprobeerd = []
    for m in stub.calls:
        if m not in geprobeerd:
            geprobeerd.append(m)

    if verwacht_fout:
        ok = (not gelukt) and verwacht_fout in fout
        detail = f"fout={fout[:60]!r}"
    else:
        ok = gelukt and stub.calls[-1] == verwacht_model
        detail = f"gebruikt={stub.calls[-1] if stub.calls else None}"
    print(f"  [{'OK ' if ok else 'FOUT'}] {naam}: {detail}, "
          f"modellen geprobeerd={geprobeerd}, calls={len(stub.calls)}")
    return ok


def main():
    r = []
    # 1. Eerste model ligt eruit met 503 → moet uitwijken naar het tweede.
    r.append(scenario("503 op model 1 → wijkt uit",
                      {"gemini-flash-latest": 503, "gemini-3.7-flash": GOED},
                      verwacht_model="gemini-3.7-flash"))

    # 2. Precies run #12: alle modellen 503 → duidelijke fout, geen stilte.
    r.append(scenario("alles 503 → faalt luid", {},
                      verwacht_fout="geen enkel Gemini-model beschikbaar"))

    # 3. 400/403 gaat over de sleutel: uitwijken is zinloos, meteen stoppen.
    r.append(scenario("400 → stopt direct, geen uitwijk",
                      {"gemini-flash-latest": 400},
                      verwacht_fout="Gemini gaf HTTP 400"))

    # 4. Onbestaand model → direct door, zonder vier keer te herkansen.
    r.append(scenario("404 → meteen volgend model",
                      {"gemini-flash-latest": 404, "gemini-3.7-flash": GOED},
                      verwacht_model="gemini-3.7-flash"))

    # 5. Gewone dag: eerste model werkt, geen omweg.
    r.append(scenario("model 1 werkt → geen uitwijk",
                      {"gemini-flash-latest": GOED},
                      verwacht_model="gemini-flash-latest"))

    print(f"\n  {sum(r)}/{len(r)} geslaagd")
    return 0 if all(r) else 1


if __name__ == "__main__":
    sys.exit(main())

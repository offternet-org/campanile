# DEVELOPED BY CARROTSTUDIO software house
"""Fills a Campanile's board as people would: posts and notices put together from many pieces,
so the text doesn't repeat more than real text does (nginx compresses it, and a board of copies
would shrink unrealistically). Each post carries a mark of its own, [A-017], so a copy of it is
recognised anywhere, byte for byte.

    seed.py DATABASE PREFIX COUNT SEED [max]

"max" fills every field to the length the board accepts (text 500, area 80, contact 120): the
largest board a phone can be sent, for the worst case.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, "/h/campanile")
import store

NEED = ["Cerco", "Mi serve", "Ci servono", "Avremmo bisogno di", "Qualcuno ha", "Chiedo"]
OFFER = ["Offro", "Ho in più", "Posso dare", "Metto a disposizione", "Regalo", "Presto"]
THINGS = [
    "acqua potabile",
    "insulina rapida",
    "pannolini taglia 4",
    "latte in polvere",
    "pile AA",
    "una torcia",
    "un caricabatterie USB-C",
    "una batteria esterna",
    "pane",
    "scatolame",
    "coperte",
    "un fornelletto a gas",
    "una radio a pile",
    "candele",
    "un passaggio in auto",
    "strisce per la glicemia",
    "antibiotico pediatrico",
    "cibo per gatti",
    "un generatore",
    "taniche vuote",
    "sacchi a pelo",
    "un materasso",
    "guanti da lavoro",
    "un secchio",
    "assorbenti",
    "farmaci per la pressione",
    "una sedia a rotelle",
    "un termometro",
]
WHY = [
    "per mia madre",
    "per un neonato",
    "per due anziani al terzo piano",
    "per la famiglia",
    "per un vicino malato",
    "per chi è rimasto senza casa",
    "per stanotte",
    "fino a domani",
    "per chi non può scendere",
    "per tre bambini",
]
DETAIL = [
    "Suonate due volte, rispondiamo anche al citofono.",
    "Siamo in casa fino a sera.",
    "Portate un contenitore pulito.",
    "Se non rispondo lasciate un biglietto sotto la porta.",
    "Porto io su per le scale.",
    "Passo in cortile alle {h}.",
    "Chiedete di {n}.",
    "Interno {i}, scala {s}.",
    "Dopo le {h} chiedete al portinaio.",
    "Solo per stasera.",
    "Va bene anche poco.",
    "Chi ne ha di più ne lasci per gli altri.",
]
AREAS = [
    "piano terra",
    "piano 1",
    "piano 2",
    "piano 3",
    "piano 4",
    "cortile",
    "via Roma 12",
    "via Garibaldi 3",
    "scala B",
    "portineria",
    "parcheggio",
    "palestra della scuola",
]
NAMES = [
    "Maria",
    "Luca",
    "Giulia",
    "Ahmed",
    "Rosa",
    "Paolo",
    "Elena",
    "Marco",
    "Fatima",
    "Gianni",
    "Chiara",
    "Omar",
    "Sofia",
    "Andrea",
    "Ling",
    "Matteo",
    "Irina",
    "Davide",
]


def sentence(rng):
    words = rng.choice(DETAIL)
    return words.format(
        h=f"{rng.randint(7, 21)}:{rng.choice(['00', '15', '30', '45'])}",
        n=rng.choice(NAMES),
        i=rng.randint(1, 40),
        s=rng.choice("ABCD"),
    )


def fill(rng, text, length):
    """Text grown with more real-sounding sentences until it is exactly `length` long."""
    while len(text) < length:
        text += " " + sentence(rng)
    text = text[:length].rstrip()
    return text + "." * (length - len(text))


def main(path, prefix, count, seed, full):
    rng = random.Random(seed)
    db = store.Store(Path(path))
    for i in range(count):
        kind = rng.choice(store.POST_KINDS)
        mark = f"[{prefix}-{i:03d}]"
        verb = rng.choice(NEED if kind == "need" else OFFER)
        text = f"{verb} {rng.choice(THINGS)} {rng.choice(WHY)}. {sentence(rng)}"
        area = rng.choice(AREAS)
        contact = f"{rng.choice(NAMES)}, interno {rng.randint(1, 40)}"
        if full:
            text = fill(rng, text, 500 - len(mark) - 1)
            area = fill(rng, area + ",", 80)
            contact = fill(rng, contact + ",", 120)
        db.add_post(kind, rng.choice(store.CATEGORIES), f"{text} {mark}", area, contact)
    for i in range(3):
        db.add_notice(
            f"Avviso {prefix}-{i}",
            f"Distribuzione acqua in cortile alle {9 + i * 3}:00. [{prefix}-N{i}]",
            i == 0,
        )
    db.close()
    print(
        f"seeded {count} posts and 3 notices marked {prefix}"
        + (", every field full" if full else "")
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5:] == ["max"])

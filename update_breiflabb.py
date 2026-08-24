import csv
import io
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime

YEAR = datetime.now().year
URL = f"https://register.fiskeridir.no/uttrekk/fangstdata_{YEAR}.csv.zip"
OUTPUT = "breiflabb_latest.csv"

FARTOY = {
    ("øyavåg", "ST0122F"): ("Øyavåg", "ST-122-F"),
    ("egil junior", "TR0090F"): ("Egil Junior", "TR-90-F"),
    ("frøyfisk", "ST0023F"): ("Frøyfisk", "ST-23-F"),
    ("mercur", "TR0011F"): ("Mercur", "TR-11-F"),
    ("sjøsvanen", "TR0047F"): ("Sjøsvanen", "TR-47-F"),
    ("junior", "TR0195F"): ("Junior", "TR-195-F"),
    ("frøymann", "TR0048F"): ("Frøymann", "TR-48-F"),
}

ALIASES = {
    "dokumenttype_kode": [
        "Dokumenttype (kode)",
        "Dokumenttype kode",
        "Dokumenttypekode",
    ],
    "dokumenttype_navn": [
        "Dokumenttype",
        "Dokumenttype navn",
    ],
    "dokumentnummer": [
        "Dokumentnummer",
        "Dokument nr",
        "Dokumentnr",
    ],
    "linjenummer": [
        "Linjenummer",
        "Linje nummer",
        "Linjenr",
    ],
    "versjon": [
        "Dokument versjonsnummer",
        "Dokumentversjon",
        "Dokument versjon",
        "Versjon",
    ],
    "landingsdato": [
        "Landingsdato",
        "Landings dato",
    ],
    "art": [
        "Art - FDIR",
        "Art",
        "Art navn",
    ],
    "rundvekt": [
        "Rundvekt",
        "Rund vekt",
        "Rundvekt kg",
    ],
    "fartoynavn": [
        "Fartøynavn",
        "Fartøy navn",
    ],
    "fartoymerke": [
        "Registreringsmerke (seddel)",
        "Fartøymerke",
        "Fartøy merke",
        "Registreringsmerke",
        "Merke",
    ],
}


def normaliser(verdi):
    return " ".join(
        (verdi or "")
        .replace("\ufeff", "")
        .replace("\u00a0", " ")
        .strip()
        .split()
    )


def normaliser_merke(verdi):
    return (
        normaliser(verdi)
        .upper()
        .replace("-", "")
        .replace(" ", "")
    )


def finn_kolonne(headers, alternativer, valgfri=False):
    oppslag = {
        normaliser(h).casefold(): h
        for h in headers
    }

    for navn in alternativer:
        key = normaliser(navn).casefold()
        if key in oppslag:
            return oppslag[key]

    if valgfri:
        return None

    raise RuntimeError(
        f"Fant ikke nødvendig kolonne. "
        f"Prøvde {alternativer}. "
        f"Kolonnene i filen er: {headers}"
    )


def til_tall(verdi):
    s = (
        (verdi or "")
        .strip()
        .replace(" ", "")
        .replace("\u00a0", "")
    )

    if not s:
        return 0.0

    if "," in s and "." not in s:
        s = s.replace(",", ".")
    elif "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")

    return float(s)


def til_versjon(verdi):
    try:
        return int(float((verdi or "0").replace(",", ".")))
    except Exception:
        return 0


def er_sluttseddel(row, kodekolonne, navnkolonne):
    kode = ""
    navn = ""

    if kodekolonne:
        kode = normaliser(row.get(kodekolonne, ""))

    if navnkolonne:
        navn = normaliser(row.get(navnkolonne, ""))

    kode = kode.replace(",", ".")

    if kode in {"0", "0.0", "00"}:
        return True

    if navn.casefold() == "sluttseddeldokument":
        return True

    return False


print("Laster ned:", URL)

req = urllib.request.Request(
    URL,
    headers={"User-Agent": "Mozilla/5.0 breiflabb-data"}
)

with urllib.request.urlopen(req, timeout=180) as response:
    zip_data = response.read()

with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
    csv_files = [
        navn for navn in z.namelist()
        if navn.lower().endswith(".csv")
    ]

    if not csv_files:
        raise RuntimeError("Fant ingen CSV-fil i ZIP-filen")

    with z.open(csv_files[0]) as f:
        text = io.TextIOWrapper(
            f,
            encoding="utf-8-sig",
            newline=""
        )

        reader = csv.DictReader(
            text,
            delimiter=";"
        )

        headers = reader.fieldnames or []

        kol = {
            "dokumenttype_kode": finn_kolonne(
                headers,
                ALIASES["dokumenttype_kode"],
                valgfri=True
            ),
            "dokumenttype_navn": finn_kolonne(
                headers,
                ALIASES["dokumenttype_navn"],
                valgfri=True
            ),
            "dokumentnummer": finn_kolonne(
                headers,
                ALIASES["dokumentnummer"]
            ),
            "linjenummer": finn_kolonne(
                headers,
                ALIASES["linjenummer"]
            ),
            "versjon": finn_kolonne(
                headers,
                ALIASES["versjon"],
                valgfri=True
            ),
            "landingsdato": finn_kolonne(
                headers,
                ALIASES["landingsdato"]
            ),
            "art": finn_kolonne(
                headers,
                ALIASES["art"]
            ),
            "rundvekt": finn_kolonne(
                headers,
                ALIASES["rundvekt"]
            ),
            "fartoynavn": finn_kolonne(
                headers,
                ALIASES["fartoynavn"]
            ),
            "fartoymerke": finn_kolonne(
                headers,
                ALIASES["fartoymerke"]
            ),
        }

        siste = {}
        treff = Counter()

        for row in reader:

            art = normaliser(
                row.get(kol["art"], "")
            )

            if art.casefold() != "breiflabb":
                continue

            treff["breiflabb"] += 1

            if not er_sluttseddel(
                row,
                kol["dokumenttype_kode"],
                kol["dokumenttype_navn"]
            ):
                continue

            treff["sluttseddel"] += 1

            navn_raw = normaliser(
                row.get(kol["fartoynavn"], "")
            )

            merke_raw = normaliser_merke(
                row.get(kol["fartoymerke"], "")
            )

            nokkel = (
                navn_raw.casefold(),
                merke_raw
            )

            if nokkel not in FARTOY:
                continue

            treff["valgte_fartoy"] += 1

            visningsnavn, visningsmerke = FARTOY[nokkel]

            dokumentnummer = normaliser(
                row.get(kol["dokumentnummer"], "")
            )

            linjenummer = normaliser(
                row.get(kol["linjenummer"], "")
            )

            if not dokumentnummer or not linjenummer:
                continue

            if kol["versjon"]:
                versjon = til_versjon(
                    row.get(kol["versjon"], "")
                )
            else:
                versjon = 0

            rundvekt = til_tall(
                row.get(kol["rundvekt"], "")
            )

            landingsdato = normaliser(
                row.get(kol["landingsdato"], "")
            )

            data = {
                "Dokumentnummer": dokumentnummer,
                "Linjenummer": linjenummer,
                "Dokumentversjon": versjon,
                "Landingsdato": landingsdato,
                "Fartøynavn": visningsnavn,
                "Fartøymerke": visningsmerke,
                "Art": "Breiflabb",
                "Rundvekt": rundvekt,
                "Halevekt": rundvekt / 2.8,
            }

            key = (
                dokumentnummer,
                linjenummer
            )

            gammel = siste.get(key)

            if (
                gammel is None
                or versjon >= gammel["Dokumentversjon"]
            ):
                siste[key] = data


rader = list(siste.values())

if not rader:
    raise RuntimeError(
        "Ingen gyldige rader funnet. "
        "Eksisterende CSV blir ikke overskrevet."
    )

rader.sort(
    key=lambda r: (
        r["Landingsdato"],
        r["Fartøynavn"],
        r["Dokumentnummer"],
        r["Linjenummer"],
    )
)

felter = [
    "Dokumentnummer",
    "Linjenummer",
    "Dokumentversjon",
    "Landingsdato",
    "Fartøynavn",
    "Fartøymerke",
    "Art",
    "Rundvekt",
    "Halevekt",
]

with open(
    OUTPUT,
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=felter,
        delimiter=";"
    )

    writer.writeheader()

    for rad in rader:
        ut = dict(rad)

        ut["Rundvekt"] = (
            f"{rad['Rundvekt']:.3f}"
            .replace(".", ",")
        )

        ut["Halevekt"] = (
            f"{rad['Halevekt']:.3f}"
            .replace(".", ",")
        )

        writer.writerow(ut)

print("Ferdig")
print("Breiflabb:", treff["breiflabb"])
print("Sluttsedler:", treff["sluttseddel"])
print("Valgte fartøy:", treff["valgte_fartoy"])
print("Eksporterte linjer:", len(rader))

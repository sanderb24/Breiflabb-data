import csv
import io
import urllib.request
import zipfile
from datetime import datetime

YEAR = datetime.now().year
URL = f"https://register.fiskeridir.no/uttrekk/fangstdata_{YEAR}.csv.zip"
OUTPUT = "breiflabb_latest.csv"

FARTOY = {
    "ST-122-F": "Øyavåg",
    "TR-90-F": "Egil Junior",
    "ST-23-F": "Frøyfisk",
    "TR-11-F": "Mercur",
    "TR-47-F": "Sjøsvanen",
    "TR-195-F": "Junior",
    "TR-48-F": "Frøymann",
}

ALIASES = {
    "dokumenttype": [
        "Dokumenttype (kode)",
        "Dokumenttype kode",
        "Dokumenttype",
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
        .strip()
        .split()
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
        return int(
            float(
                (verdi or "0").replace(",", ".")
            )
        )
    except Exception:
        return 0


print("Laster ned:", URL)

req = urllib.request.Request(
    URL,
    headers={
        "User-Agent": "Mozilla/5.0 breiflabb-data"
    }
)

with urllib.request.urlopen(
    req,
    timeout=180
) as response:
    zip_data = response.read()

print(
    "Nedlasting ferdig:",
    len(zip_data),
    "bytes"
)

with zipfile.ZipFile(
    io.BytesIO(zip_data)
) as z:

    csv_files = [
        navn
        for navn in z.namelist()
        if navn.lower().endswith(".csv")
    ]

    if not csv_files:
        raise RuntimeError(
            "Fant ingen CSV-fil i ZIP-filen"
        )

    csv_name = csv_files[0]

    print("Leser:", csv_name)

    with z.open(csv_name) as f:

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
            "dokumenttype": finn_kolonne(
                headers,
                ALIASES["dokumenttype"]
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
            "fartoymerke": finn_kolonne(
                headers,
                ALIASES["fartoymerke"]
            ),
        }

        print("Kolonner brukt:")
        for navn, kolonnenavn in kol.items():
            print(navn, "->", kolonnenavn)

        siste = {}
        treff = 0

        for row in reader:

            dokumenttype = normaliser(
                row.get(
                    kol["dokumenttype"],
                    ""
                )
            )

            if dokumenttype != "0":
                continue

            art = normaliser(
                row.get(
                    kol["art"],
                    ""
                )
            )

            if art.casefold() != "breiflabb":
                continue

            merke = normaliser(
                row.get(
                    kol["fartoymerke"],
                    ""
                )
            ).upper()

            if merke not in FARTOY:
                continue

            dokumentnummer = normaliser(
                row.get(
                    kol["dokumentnummer"],
                    ""
                )
            )

            linjenummer = normaliser(
                row.get(
                    kol["linjenummer"],
                    ""
                )
            )

            if kol["versjon"]:
                versjon = til_versjon(
                    row.get(
                        kol["versjon"],
                        ""
                    )
                )
            else:
                versjon = 0

            rundvekt = til_tall(
                row.get(
                    kol["rundvekt"],
                    ""
                )
            )

            landingsdato = normaliser(
                row.get(
                    kol["landingsdato"],
                    ""
                )
            )

            data = {
                "Dokumentnummer": dokumentnummer,
                "Linjenummer": linjenummer,
                "Dokumentversjon": versjon,
                "Landingsdato": landingsdato,
                "Fartøynavn": FARTOY[merke],
                "Fartøymerke": merke,
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
                or versjon
                >= gammel["Dokumentversjon"]
            ):
                siste[key] = data

            treff += 1


rader = list(
    siste.values()
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

print(
    f"Ferdig. Fant {treff} "
    f"breiflabb-linjer og lagret "
    f"{len(rader)} siste "
    f"dokumentversjoner i {OUTPUT}"
)

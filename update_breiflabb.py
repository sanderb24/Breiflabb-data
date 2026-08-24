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
    "ST-122-F": "Øyavåg",
    "TR-90-F": "Egil Junior",
    "ST-23-F": "Frøyfisk",
    "TR-11-F": "Mercur",
    "TR-47-F": "Sjøsvanen",
    "TR-195-F": "Junior",
    "TR-48-F": "Frøymann",
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

    kode_normalisert = kode.replace(",", ".").strip()

    if kode_normalisert in {"0", "0.0", "00"}:
        return True

    if navn.casefold() == "sluttseddeldokument":
        return True

    return False


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
            "fartoymerke": finn_kolonne(
                headers,
                ALIASES["fartoymerke"]
            ),
        }

        print("Kolonner brukt:")
        for navn, kolonnenavn in kol.items():
            print(f"  {navn}: {kolonnenavn}")

        if not kol["dokumenttype_kode"] and not kol["dokumenttype_navn"]:
            raise RuntimeError(
                "Fant verken dokumenttypekode eller dokumenttypenavn."
            )

        total = 0
        breiflabb_treff = 0
        sluttseddel_treff = 0
        fartoy_treff = 0

        artverdier = Counter()
        dokumenttyper = Counter()
        fartoymerker = Counter()

        siste = {}

        for row in reader:
            total += 1

            art = normaliser(
                row.get(
                    kol["art"],
                    ""
                )
            )

            artverdier[art] += 1

            if art.casefold() != "breiflabb":
                continue

            breiflabb_treff += 1

            kodeverdi = ""
            navnverdi = ""

            if kol["dokumenttype_kode"]:
                kodeverdi = normaliser(
                    row.get(
                        kol["dokumenttype_kode"],
                        ""
                    )
                )

            if kol["dokumenttype_navn"]:
                navnverdi = normaliser(
                    row.get(
                        kol["dokumenttype_navn"],
                        ""
                    )
                )

            dokumenttyper[
                f"kode={kodeverdi!r}, navn={navnverdi!r}"
            ] += 1

            if not er_sluttseddel(
                row,
                kol["dokumenttype_kode"],
                kol["dokumenttype_navn"]
            ):
                continue

            sluttseddel_treff += 1

            merke = normaliser(
                row.get(
                    kol["fartoymerke"],
                    ""
                )
            ).upper()

            fartoymerker[merke] += 1

            if merke not in FARTOY:
                continue

            fartoy_treff += 1

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

            if not dokumentnummer:
                continue

            if not linjenummer:
                continue

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
                or versjon >= gammel["Dokumentversjon"]
            ):
                siste[key] = data


print()
print("DIAGNOSTIKK")
print("-----------")
print("Totale rader:", total)
print("Breiflabb-rader:", breiflabb_treff)
print("Sluttseddel-rader for Breiflabb:", sluttseddel_treff)
print("Rader på valgte fartøy:", fartoy_treff)

print()
print("Dokumenttyper for Breiflabb:")
for verdi, antall in dokumenttyper.most_common(20):
    print(f"  {verdi}: {antall}")

print()
print("Registreringsmerker etter Breiflabb + sluttseddel:")
for merke, antall in fartoymerker.most_common(30):
    print(f"  {merke!r}: {antall}")


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


if breiflabb_treff == 0:
    raise RuntimeError(
        "Fant ingen Breiflabb-rader. "
        "Art-filteret må kontrolleres."
    )

if sluttseddel_treff == 0:
    raise RuntimeError(
        "Fant Breiflabb, men ingen sluttsedler. "
        "Dokumenttypefilteret må kontrolleres."
    )

if fartoy_treff == 0:
    raise RuntimeError(
        "Fant Breiflabb-sluttsedler, men ingen av de valgte fartøyene. "
        "Kontroller registreringsmerkene i loggen."
    )

if not rader:
    raise RuntimeError(
        "Ingen rader klare for eksport. "
        "Eksisterende breiflabb_latest.csv blir derfor ikke overskrevet."
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


print()
print(
    f"Ferdig. Lagret {len(rader)} "
    f"siste dokumentlinjer i {OUTPUT}"
)

print()
print("Fordeling på fartøy:")

fordeling = Counter(
    r["Fartøynavn"]
    for r in rader
)

for fartoy, antall in sorted(
    fordeling.items()
):
    print(
        f"  {fartoy}: {antall} linjer"
    )

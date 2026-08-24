import csv
import io
import urllib.request
import zipfile
from datetime import datetime

YEAR = datetime.now().year
URL = f"https://register.fiskeridir.no/uttrekk/fangstdata_{YEAR}.csv.zip"
OUTPUT = "breiflabb_latest.csv"

FARTOY = {
    "øyavåg": ("Øyavåg", "ST-122-F"),
    "egil junior": ("Egil Junior", "TR-90-F"),
    "frøyfisk": ("Frøyfisk", "ST-23-F"),
    "mercur": ("Mercur", "TR-11-F"),
    "sjøsvanen": ("Sjøsvanen", "TR-47-F"),
    "junior": ("Junior", "TR-195-F"),
    "frøymann": ("Frøymann", "TR-48-F"),
}

# Sikre identifikatorer
JUNIOR_RAA_MERKE = "TR0195F"
EGIL_JUNIOR_KALLESIGNAL = "LH5006"
EGIL_JUNIOR_MERKER = {
    "TR0090F",
    "T0090F",
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
    "radiokallesignal": [
        "Radiokallesignal (seddel)",
        "Radiokallesignal",
        "Kallesignal",
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
        f"Fant ikke nødvendig kolonne. Prøvde: {alternativer}"
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


def er_sluttseddel(row, kodekolonne, navnkolonne):
    kode = ""
    navn = ""

    if kodekolonne:
        kode = normaliser(
            row.get(kodekolonne, "")
        )

    if navnkolonne:
        navn = normaliser(
            row.get(navnkolonne, "")
        )

    kode = kode.replace(",", ".")

    if kode in {"0", "0.0", "00"}:
        return True

    if navn.casefold() == "sluttseddeldokument":
        return True

    return False


def identifiser_fartoy(navn_raw, merke_raw, kallesignal_raw):
    navn_key = normaliser(navn_raw).casefold()
    merke_key = normaliser_merke(merke_raw)
    kallesignal = normaliser(kallesignal_raw).upper()

    # --------------------------------------------------
    # EGIL JUNIOR
    # --------------------------------------------------
    # Bruk flere mulige identifikatorer slik at han ikke
    # forsvinner hvis fartøynavnet i råfila er skrevet
    # annerledes.
    if (
        kallesignal == EGIL_JUNIOR_KALLESIGNAL
        or merke_key in EGIL_JUNIOR_MERKER
        or (
            "egil" in navn_key
            and "junior" in navn_key
        )
    ):
        return (
            "Egil Junior",
            "TR-90-F"
        )

    # --------------------------------------------------
    # JUNIOR
    # --------------------------------------------------
    # Det finnes flere båter som heter Junior.
    if navn_key == "junior":
        if merke_key == JUNIOR_RAA_MERKE:
            return (
                "Junior",
                "TR-195-F"
            )

        return None

    # --------------------------------------------------
    # ØVRIGE FARTØY
    # --------------------------------------------------
    if navn_key in FARTOY:
        return FARTOY[navn_key]

    return None


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

            "radiokallesignal": finn_kolonne(
                headers,
                ALIASES["radiokallesignal"],
                valgfri=True
            ),
        }

        siste = {}

        antall_breiflabb = 0
        antall_sluttseddel = 0
        antall_valgte = 0
        egil_treff = 0

        for row in reader:

            art = normaliser(
                row.get(
                    kol["art"],
                    ""
                )
            )

            if art.casefold() != "breiflabb":
                continue

            antall_breiflabb += 1

            if not er_sluttseddel(
                row,
                kol["dokumenttype_kode"],
                kol["dokumenttype_navn"]
            ):
                continue

            antall_sluttseddel += 1


            navn_raw = normaliser(
                row.get(
                    kol["fartoynavn"],
                    ""
                )
            )

            merke_raw = normaliser(
                row.get(
                    kol["fartoymerke"],
                    ""
                )
            )

            kallesignal_raw = ""

            if kol["radiokallesignal"]:
                kallesignal_raw = normaliser(
                    row.get(
                        kol["radiokallesignal"],
                        ""
                    )
                )


            fartoy = identifiser_fartoy(
                navn_raw,
                merke_raw,
                kallesignal_raw
            )

            if fartoy is None:
                continue


            visningsnavn, visningsmerke = fartoy

            antall_valgte += 1

            if visningsnavn == "Egil Junior":
                egil_treff += 1


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


            versjon = 0

            if kol["versjon"]:
                versjon = til_versjon(
                    row.get(
                        kol["versjon"],
                        ""
                    )
                )


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
                "Dokumentnummer":
                    dokumentnummer,

                "Linjenummer":
                    linjenummer,

                "Dokumentversjon":
                    versjon,

                "Landingsdato":
                    landingsdato,

                "Fartøynavn":
                    visningsnavn,

                "Fartøymerke":
                    visningsmerke,

                "Art":
                    "Breiflabb",

                "Rundvekt":
                    rundvekt,

                "Halevekt":
                    rundvekt / 2.8,
            }


            key = (
                dokumentnummer,
                linjenummer
            )

            gammel = siste.get(key)

            if (
                gammel is None
                or versjon >=
                gammel["Dokumentversjon"]
            ):
                siste[key] = data


rader = list(
    siste.values()
)


if not rader:
    raise RuntimeError(
        "Ingen gyldige rader funnet. "
        "CSV blir ikke overskrevet."
    )


def dato_sort(rad):
    try:
        return datetime.strptime(
            rad["Landingsdato"],
            "%d.%m.%Y"
        )
    except Exception:
        return datetime.min


rader.sort(
    key=lambda r: (
        dato_sort(r),
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


print()
print("FERDIG")
print("Breiflabb:", antall_breiflabb)
print("Sluttsedler:", antall_sluttseddel)
print("Valgte fartøy:", antall_valgte)
print("Egil Junior-rader:", egil_treff)
print("Eksporterte linjer:", len(rader))

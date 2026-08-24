import csv
import io
import urllib.request
import zipfile
from datetime import datetime

YEAR = datetime.now().year
URL = f"https://register.fiskeridir.no/uttrekk/fangstdata_{YEAR}.csv.zip"

FARTOY = {
    "ST-122-F": "Øyavåg",
    "TR-90-F": "Egil Junior",
    "ST-23-F": "Frøyfisk",
    "TR-11-F": "Mercur",
    "TR-47-F": "Sjøsvanen",
    "TR-195-F": "Junior",
    "TR-48-F": "Frøymann",
}

print("Laster ned:", URL)

req = urllib.request.Request(
    URL,
    headers={"User-Agent": "Mozilla/5.0"}
)

with urllib.request.urlopen(req, timeout=180) as response:
    zip_data = response.read()

print("Nedlasting ferdig:", len(zip_data), "bytes")

with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
    csv_files = [x for x in z.namelist() if x.lower().endswith(".csv")]

    if not csv_files:
        raise RuntimeError("Fant ingen CSV i ZIP-filen")

    with z.open(csv_files[0]) as f:
        text = io.TextIOWrapper(f, encoding="utf-8-sig")
        reader = csv.DictReader(text, delimiter=";")

        print("Kolonner funnet:")
        print(reader.fieldnames)

        rows = list(reader)

print("Antall rader:", len(rows))

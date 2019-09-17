import csv
from pymarc_helpers import *
from pymarc import Record, Field
import datetime
import re
from sys import argv

part1 = "sourcefiles/0-600.csv"
part2 = "sourcefiles/601-1200.csv"
part3 = "sourcefiles/1201-1800.csv"
part4 = "sourcefiles/1801-Ende.csv"

# output nur schreiben wenn write_out als kommandozeilenargument gegeben wird
write_output = False
if len(argv) > 1:
    if argv[1] == "write_out":
        write_output = True
def csv_to_list(filename):
    """Read a csv file and return a list of dicts (one per line)"""

    rows = []
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter="\t")
        for row in reader:
            if "*" in row["Signatur modern"]:
                continue
            else:
                rows.append(row)

    return rows

vb_pers = {}
with open("sourcefiles/Namensansetzung_Kern_Alma.csv") as csvfile:
    reader = csv.reader(csvfile, delimiter='\t')
    for row in reader:
        vb_pers[row[0].strip()] = ['a', row[1].strip(), 'c', row[2].strip(), '0', row[3].strip()]
vb_kor = {}
with open("sourcefiles/vb_kor.csv") as csvfile:
    reader = csv.reader(csvfile, delimiter='\t')
    for row in reader:
        vb_kor[row[0].strip()] = ['a', row[1].strip(), '0', row[2].strip()]
def get_date(row):
    """Return the raw date for 264 $$c and 008"""
    data = None

    if row["1. Dat. exakt"].strip():
        data = row["1. Dat. exakt"].strip()
    elif row["1. Dat. Ex. Von - bis"].strip():
        data = row["1. Dat. Ex. Von - bis"].strip()
    elif row['1. Dat. ca., um, vor, Anfang, Ende'].strip():
        data = row['1. Dat. ca., um, vor, Anfang, Ende'].strip()
    elif row["1. Dat. Jh. "].strip():
        data = row["1. Dat. Jh. "].strip()
    else:
        data = "Datum unbekannt"

    return data
def create_record(row):
    """Take a  row from the csv dict and return a pymarc.Record"""
    rec = Record()
    rec.leader = "00000ntm#a22000005c#4500"
    rec.add_ordered_field(
        pymarc.Field(
            tag = "005",
            data = datetime.datetime.now().strftime("%Y%m%d%H%M%S.0")
        ))
    # generiere Inhalt für 245
    if not row['Signatur modern']:
        return "Keine Signatur vorhanden"
    else:
        if row["Bd."]:
            val245 = f"UBG Ms {row['Signatur modern'].strip()}/{row['Bd.'].strip()}"
        else:
            val245 = f"UBG Ms {row['Signatur modern'].strip()}"
    
        rec.add_ordered_field(
            Field(
                tag = '245',
                indicators = ['0', '0'],
                subfields = ['a', val245]))
    
    # Umfangsangabe in 300
    if "rolle" in row["Umfang"].lower():
        sfa = row["Umfang"].strip()
    else:
        sfa = f'{row["Umfang"].strip()} Blätter'
    
    sfc = f'{row["Format"].strip()}, {row["Größe h : b   "].strip().replace(":", "x")}'
    
    if sfa.startswith(" "):
        sfa = ""
    if sfc.startswith(", "):
        sfc = sfc[2:]
    if sfc.endswith(", "):
        sfc = sfc[:-2]
    rec.add_ordered_field(
        Field(
            tag = '300',
            indicators = [' ', ' '],
            subfields = ["a", sfa, "c", sfc]))
    if row["Signatur alt"]:
        rec.add_field(
            Field(
                tag = '500',
                indicators = [' ', ' '],
                subfields = ['a', f'Historische Signatur der Universitätsbibliothek Graz: {row["Signatur alt"].strip()}'])
        )
    rec.add_ordered_field(
        Field(
            tag = "500",
            indicators = [" ", " "],
            subfields = ["a", "Stand 2018"])
    )
    beschreibstoff = row["Beschreibstoff"].strip()
    rec.add_ordered_field(
        Field(
            tag = "340",
            indicators = [" ", " "],
            subfields = ["a", beschreibstoff])
    )
    rec.add_ordered_field(
        pymarc.Field(
            tag = "264",
            indicators = [" ", "1"],
            subfields = ["c", f"[{get_date(row)}]"]))
    
    rec.add_field(
        Field(
            tag = "710",
            indicators = ["2", " "],
            subfields = ["a", "Universitätsbibliothek Graz", "0", "(DE-588)18018-X", "4", "own"]
        ))
    date = get_date(row)

    if date == "Datum unbekannt":
        print("Kein Datum vorhanden: " + val245)
        return f"{val245}: Kein Datum vorhanden"
    else:
        year = date_008(date)
        if year is None:
            print("Keine Jahreszahl für 008 extrahierbar: " + val245)
            return f"{val245}: Keine Jahreszahl für 008 extrahierbar."

    date_on_file = datetime.datetime.now().strftime("%y%m%d")
    data008 = date_on_file + "s" + year + "    " + "xx " + "||||"  "|" + " " + "||||" + " 00||||   ||"
    rec.add_ordered_field(
        Field(tag = "008",
              data = data008)
    )
    vorbes_nat_pers = []
    if row["1. VB natürl. Personen"] != '':
        vorbes_nat_pers.append(row["1. VB natürl. Personen"].strip())
    if row["2. VB natürl. Personen"] != '':
        vorbes_nat_pers.append(row["2. VB natürl. Personen"].strip())
    
    if len(vorbes_nat_pers) > 0:
        for pers in vorbes_nat_pers:
            if pers not in vb_pers:
                print(f"Person nicht vorhanden: {pers}")
                continue
            else:
                persfield = Field(
                    tag = '700',
                    indicators = ['1', ' '],
                    subfields = vb_pers[pers] + ['4', 'fmo'])
                if "," not in vb_pers[pers][1]:
                    persfield.indicators = ['0', ' ']
                rec.add_ordered_field(persfield)
    vorbes_kor = []
    if row["1. Vorbesitz Institution"] != '':
        vorbes_kor.append(row["1. Vorbesitz Institution"].strip())
    if row["2. Vorbesitz Institution"] != '':
        vorbes_kor.append(row["2. Vorbesitz Institution"].strip())
    
    if len(vorbes_kor) > 0:
        for kor in vorbes_kor:
            if kor not in vb_kor:
                korfield = Field(
                    tag = '710',
                    indicators = ['2', ' '],
                    subfields = ['a', kor, '4', 'fmo'])
                rec.add_ordered_field(korfield)
                print(korfield)
            else:
                korfield = Field(
                    tag = '710',
                    indicators = ['2', ' '],
                    subfields = vb_kor[kor] + ['4', 'fmo'])
                rec.add_ordered_field(korfield)
    standort = "SSHS"
    signatur = "Ms " + row["Signatur modern"]
    
    rec.add_field(
        Field(
            tag = "995",
            indicators = [" ", " "],
            subfields = ["b", "BHB", 
                         "c", standort,
                         "h", signatur,
                         "a", row["Signatur alt"],
                         "9", "LOCAL"
                         ]
        ))
    
    return rec
map_dates_008 = {
    "VI": "501",
    "IX/1": "801",
    "Mitte IX": "851",
    "Ende IX": "881",
    "Anfang X": "901",
    "Mitte X": "951",
    "Ende X": "981",
    "X": "901",
    "X/1": "901",
    "X/2": "951",
    "Anfang XI": "1001",
    "Mitte XI": "1051",
    "Ende XI": "1081",
    "XI": "1051",
    "XI/1": "1001",
    "XI/2": "1051",
    "Anfang XII": "1101",
    "Mitte XII": "1151",
    "Ende XII": "1181",
    "XII": "1151",
    "XII/1": "1101",
    "XII/2": "1151",
    "Anfang XIII": "1201",
    "Mitte XIII": "1251",
    "Ende XIII": "1281",
    "XIII": "1251",
    "XIII/1": "1201",
    "XIII/2": "1251",
    "Anfang XIV": "1301",
    "Mitte XIV": "1351",
    "Ende XIV": "1381",
    "Spätes XIV": "1381",
    "XIV": "1351",
    "XIV/1": "1301",
    "XIV/2": "1351",
    "Anfang XV": "1401",
    "Erstes Viertel XV": "1401",
    "Mitte XV": "1451",
    "Nach Mitte XV": "1451",
    "Ende XV": "1481",
    "XV": "1451",
    "XV/1": "1401",
    "XV/2": "1451",
    "Anfang XVI": "1501",
    "Mitte XVI": "1551",
    "Ende XVI": "1581",
    "XVI": "1551",
    "XVI/1": "1501",
    "XVI/2": "1551",
    "Anfang XVII": "1601",
    "Mitte XVII": "1651",
    "Ende XVII": "1681",
    "XVII": "1651",
    "XVII/1": "1601",
    "XVII/2": "1651",
    "Anfang XVIII": "1701",
    "Vor Mitte XVIII": "1701",
    "Mitte XVIII": "1751",
    "Ende XVIII": "1781",
    "XVIII": "1751",
    "XVIII/1": "1701",
    "XVIII/2": "1751",
    "Mitte XIX": "1851",
    "XIX": "1801",
    "XIX/1": "1801",
    "XIX/2": "1851",
}
def date_008(date):
    year = None
    if date in map_dates_008.keys():
        year = map_dates_008[date].zfill(4)
    else:
        re_match = re.search(r'\d{3}\d?', date)
        if re_match is not None:
            year = re_match.group(0).strip().zfill(4)
    return year


d1 = csv_to_list(part1)
d2 = csv_to_list(part2)
d3 = csv_to_list(part3)
d4 = csv_to_list(part4)
r = d1[0]

rows = []
errors = []
outlist = []

for d in (d1, d2, d3, d4):
    for row in d:
        rows.append(row)

for row in rows:
    rec = create_record(row)
    if type(rec) is pymarc.record.Record:
        outlist.append(rec)
    else:
        errors.append(rec)

if write_output:
    write_to_file(outlist, "output/handschriften", "xml")

    with open("output/errors.txt", "w") as fh:
        for error in errors:
            fh.write(error + "\n")

# scalecraft-hunter

Turn messy raw business lists (directory exports, map scrapes, public CSVs)
into a clean, deduped lead file. Part of the ScaleCraft lead pipeline:
**hunter** (clean raw lists) → **scorer** (rank them) → **outreach** (draft emails).

Offline, stdlib-only, single file.

## What it does

- Normalizes names (`"Sharma's Dhaba Pvt. Ltd."` ≡ `"sharmas dhaba"`), phones (`+91 (98) 765-43210` → `+919876543210`), websites (adds scheme)
- Dedupes by name+city
- Validates emails; invalid ones move to notes, not silently dropped
- Flags leads missing contact info (`needs_contact_info` column)

## Usage

```
python scalecraft-hunter.py --in raw.csv --out leads.csv
python scalecraft-hunter.py --in raw.json --only-with-contact
```

## Tests

```
python -m unittest test_hunter
```

MIT

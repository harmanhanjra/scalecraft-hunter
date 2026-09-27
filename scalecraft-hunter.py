#!/usr/bin/env python3
"""ScaleCraft Hunter — clean, dedupe and qualify raw business lists into leads.

Takes messy CSV/JSON exports (directories, maps scrapes, public lists) and
produces a clean lead file: normalized names/phones/websites, deduped by
name+city, missing-contact flags. Fully offline, stdlib-only.

Usage:
    python scalecraft-hunter.py --in raw.csv --out leads.csv
    python scalecraft-hunter.py --in raw.csv --only-with-contact
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import pathlib
import re
import sys

FIELDS = ["name", "city", "category", "website", "phone", "email", "notes"]

PHONE_RE = re.compile(r"[+()\-\s]")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_name(name: str) -> str:
    """Canonical dedupe key: lowercase, strip legal suffixes and punctuation."""
    n = (name or "").lower().strip().replace("'", "")
    n = re.sub(r"\b(pvt\.?|private|ltd\.?|limited|llc|inc\.?|gmbh|and|&|the)\b", " ", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def normalize_phone(phone: str) -> str:
    raw = (phone or "").strip()
    digits = PHONE_RE.sub("", raw)
    if not digits:
        return ""
    if raw.startswith("+"):
        return "+" + digits
    if digits.startswith("00"):
        return "+" + digits[2:]
    return digits


def normalize_website(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))


def dedupe_key(lead: dict) -> tuple:
    return (normalize_name(lead.get("name", "")),
            (lead.get("city") or "").lower().strip())


def clean(raw_leads: list[dict]) -> dict:
    """Returns {leads: [...], dropped_duplicates: n, flagged: n}."""
    seen, leads, dupes, flagged = set(), [], 0, 0
    for raw in raw_leads:
        lead = {k: (raw.get(k) or "").strip() for k in FIELDS}
        lead["phone"] = normalize_phone(lead["phone"])
        lead["website"] = normalize_website(lead["website"])
        if lead["email"] and not valid_email(lead["email"]):
            lead["notes"] = (lead["notes"] + " " if lead["notes"] else "") + f"invalid-email:{lead['email']}"
            lead["email"] = ""
        key = dedupe_key(lead)
        if not key[0]:
            continue
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        missing = [f for f in ("website", "phone", "email") if not lead[f]]
        lead["needs_contact_info"] = ",".join(missing)
        if missing:
            flagged += 1
        leads.append(lead)
    return {"leads": leads, "dropped_duplicates": dupes, "flagged_missing_contact": flagged}


def load_raw(path) -> list[dict]:
    path = pathlib.Path(path)
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        doc = json.loads(text)
        return doc if isinstance(doc, list) else doc.get("leads", doc.get("records", []))
    return list(csv.DictReader(io.StringIO(text)))


def write_csv(leads: list[dict], path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS + ["needs_contact_info"])
        writer.writeheader()
        writer.writerows(leads)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="scalecraft-hunter",
                                     description="Clean and dedupe raw business lists into leads.")
    parser.add_argument("--in", dest="infile", required=True, help="raw CSV or JSON")
    parser.add_argument("--out", help="output CSV (default: stdout as JSON)")
    parser.add_argument("--only-with-contact", action="store_true",
                        help="drop leads missing all of website/phone/email")
    args = parser.parse_args(argv)

    try:
        raw = load_raw(args.infile)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    result = clean(raw)
    leads = result["leads"]
    if args.only_with_contact:
        leads = [l for l in leads if l["needs_contact_info"] != "website,phone,email"]

    if args.out:
        write_csv(leads, args.out)
        print(f"wrote {len(leads)} leads to {args.out} "
              f"({result['dropped_duplicates']} duplicates dropped, "
              f"{result['flagged_missing_contact']} flagged missing contact info)")
    else:
        print(json.dumps({"summary": {k: v for k, v in result.items() if k != "leads"},
                          "leads": leads}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

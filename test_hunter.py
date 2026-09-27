import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
def _load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(os.path.dirname(os.path.abspath(__file__)), fname))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
hu = _load('scalecraft-hunter.py', 'hu')

def raw(**kw):
    base = {"name": "", "city": "", "category": "", "website": "", "phone": "", "email": "", "notes": ""}
    base.update(kw); return base

class NormalizeTests(unittest.TestCase):
    def test_name_dedupe_key(self):
        self.assertEqual(hu.normalize_name("Sharma's Dhaba Pvt. Ltd."), hu.normalize_name("sharmas dhaba"))
        self.assertEqual(hu.normalize_name("The  Coffee  House!"), "coffee house")

    def test_phone(self):
        self.assertEqual(hu.normalize_phone("+91 (98) 765-43210"), "+919876543210")
        self.assertEqual(hu.normalize_phone("0091 9876543210"), "+919876543210")

    def test_website_scheme(self):
        self.assertEqual(hu.normalize_website("testbiz.io"), "https://testbiz.io")
        self.assertEqual(hu.normalize_website("http://x.com/"), "http://x.com")

    def test_email_validation(self):
        self.assertTrue(hu.valid_email("a@b.co"))
        self.assertFalse(hu.valid_email("nope@"))
        self.assertFalse(hu.valid_email(""))

class CleanTests(unittest.TestCase):
    def test_dedupe(self):
        out = hu.clean([raw(name="A", city="Berlin"), raw(name="A  pvt ltd", city="berlin")])
        self.assertEqual(len(out["leads"]), 1)
        self.assertEqual(out["dropped_duplicates"], 1)

    def test_flags_missing_contacts(self):
        out = hu.clean([raw(name="A")])
        self.assertEqual(out["leads"][0]["needs_contact_info"], "website,phone,email")
        self.assertEqual(out["flagged_missing_contact"], 1)

    def test_invalid_email_moved_to_notes(self):
        out = hu.clean([raw(name="A", email="broken-at-b")])
        self.assertEqual(out["leads"][0]["email"], "")
        self.assertIn("invalid-email", out["leads"][0]["notes"])

    def test_skips_blank_names(self):
        out = hu.clean([raw(name="", city="Berlin"), raw(name="A")])
        self.assertEqual(len(out["leads"]), 1)

class CliTests(unittest.TestCase):
    def test_roundtrip(self):
        import tempfile
        data = json.dumps([raw(name="A", phone="+91 98765 43210", email="a@b.co"),
                           raw(name="A private limited", phone="0091-98765-43210")])
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); f.write(data); f.close()
        out = tempfile.NamedTemporaryFile(suffix=".csv", delete=False); out.close()
        try:
            rc = hu.main(["--in", f.name, "--out", out.name])
            self.assertEqual(rc, 0)
            import csv as csvmod
            rows = list(csvmod.DictReader(open(out.name)))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["phone"], "+919876543210")
        finally:
            os.unlink(f.name); os.unlink(out.name)

if __name__ == "__main__":
    unittest.main()

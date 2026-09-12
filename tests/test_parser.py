import unittest

from scripts.update_data import (
    general_matura_criteria,
    parse_programme_html,
    programme_urls_from_catalogue,
)


class ParserTests(unittest.TestCase):
    def test_catalogue_link_discovery(self):
        html = """
        <html><body><main>
          <a href="/programi/anglistika">Anglistika</a>
          <a href="https://www.uni-lj.si/programi/arhitektura-2/">Arhitektura</a>
          <a href="/programi">Catalogue</a>
          <a href="https://example.com/programi/not-ul">Other</a>
        </main></body></html>
        """
        self.assertEqual(
            programme_urls_from_catalogue(html),
            [
                "https://www.uni-lj.si/programi/anglistika",
                "https://www.uni-lj.si/programi/arhitektura-2",
            ],
        )

    def test_general_matura_group_a_only(self):
        lines = [
            "Če bo sprejet sklep o omejitvi vpisa, bodo",
            "kandidati iz točke a) izbrani glede na:",
            "- splošni uspeh pri splošni maturi 50 % točk,",
            "- splošni uspeh v 3. in 4. letniku 20 % točk;",
            "kandidati iz točke b) izbrani glede na:",
            "- splošni uspeh pri poklicni maturi 30 % točk;",
        ]
        self.assertEqual(
            general_matura_criteria(lines),
            [
                "- splošni uspeh pri splošni maturi 50 % točk,",
                "- splošni uspeh v 3. in 4. letniku 20 % točk;",
            ],
        )

    def test_general_matura_combined_a_and_c(self):
        lines = [
            "kandidati iz točk a) in c) izbrani glede na:",
            "– uspeh pri preizkusu posebne nadarjenosti 90 % točk,",
            "– splošni uspeh pri maturi oziroma zaključnem izpitu 5 % točk;",
            "kandidati iz točke b) izbrani glede na:",
            "– splošni uspeh pri poklicni maturi 4 % točk;",
        ]
        result = general_matura_criteria(lines)
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0].startswith("- uspeh pri preizkusu"))

    def test_shared_criteria_stops_before_higher_years(self):
        lines = [
            "Če bo sprejet sklep o omejitvi vpisa, bodo kandidati, ki se vpisujejo v 1. letnik izbrani glede na:",
            "- splošni uspeh pri splošni maturi 12,5 % točk,",
            "- uspeh pri preizkusu sposobnosti 75 % točk.",
            "Vrednost posameznega dela preizkusa sposobnosti:",
            "- Prvi del 37,5 %.",
            "- Drugi del 37,5 %.",
            "Kandidati, ki se vpisujejo v višji letnik po merilih za prehode, bodo izbrani glede na:",
            "- povprečna ocena 25 % točk.",
        ]
        result = general_matura_criteria(lines)
        self.assertEqual(len(result), 5)
        self.assertNotIn("povprečna", " ".join(result))

    def test_programme_parser(self):
        html = """
        <html><head><title>Anglistika | Univerza v Ljubljani</title></head><body><main>
          <h1>Anglistika</h1>
          <div>Vrsta študijskega programa</div><div>Univerzitetni</div>
          <div>Trajanje v letih</div><div>3</div>
          <div>Št. ECTS kreditnih točk</div><div>180</div>
          <div>Članica UL</div><div>Filozofska fakulteta</div>
          <h2>Opis programa</h2>
          <p>Prvi odstavek opisa.</p><p>Drugi odstavek opisa.</p>
          <h2>Strokovni naslov</h2><p>Diplomirani anglist.</p>
          <h2>Merila za izbiro ob omejitvi vpisa za študijska leta 2025/2026 do 2028/2029</h2>
          <p>Če bo sprejet sklep o omejitvi vpisa, bodo</p>
          <p>kandidati iz točke a) izbrani glede na:</p>
          <ul><li>splošni uspeh pri splošni maturi 50 % točk,</li><li>splošni uspeh v 3. in 4. letniku 20 % točk.</li></ul>
          <p>kandidati iz točke b) izbrani glede na:</p>
          <ul><li>splošni uspeh pri poklicni maturi 30 % točk.</li></ul>
          <h2>Hitre povezave</h2>
        </main></body></html>
        """
        parsed = parse_programme_html(html, "https://www.uni-lj.si/programi/anglistika")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["name"], "Anglistika")
        self.assertEqual(parsed["faculty"], "Filozofska fakulteta")
        self.assertEqual(parsed["duration"], 3)
        self.assertEqual(parsed["description"], ["Prvi odstavek opisa.", "Drugi odstavek opisa."])
        self.assertEqual(len(parsed["criteriaGeneralMatura"]), 2)


if __name__ == "__main__":
    unittest.main()

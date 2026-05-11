import unittest

try:
    import pyphen  # noqa: F401
except ModuleNotFoundError:
    raise unittest.SkipTest("pyphen is not installed in this environment")

from core.wordlist_filter import FilterConfig, WordlistFilter, normalize_import_word


class WordlistFilterTests(unittest.TestCase):
    def test_standard_pool_rejects_lowercase_verb_and_adjective_forms(self):
        result = WordlistFilter().filter_lines(["lytisch", "anhebt", "Organteil", "Jubelchor"])
        accepted = {entry["word"] for entry in result["accepted"]}
        rejected = dict(result["rejected"])

        self.assertEqual(accepted, {"Organteil", "Jubelchor"})
        self.assertEqual(rejected["lytisch"], "kein_standard_nomen")
        self.assertEqual(rejected["anhebt"], "kein_standard_nomen")

    def test_rejects_known_plural_and_case_forms_when_base_exists(self):
        result = WordlistFilter().filter_lines([
            "Lehrtext",
            "Lehrtexte",
            "Lehrtexten",
            "Mikrodiode",
            "Mikrodioden",
            "Notenname",
            "Notennamen",
            "Notennamens",
            "Organteil",
            "Organteile",
        ])
        accepted = {entry["word"] for entry in result["accepted"]}
        rejected = dict(result["rejected"])

        self.assertEqual(accepted, {"Lehrtext", "Mikrodiode", "Notenname", "Organteil"})
        for word in ["Lehrtexte", "Lehrtexten", "Mikrodioden", "Notennamen", "Notennamens", "Organteile"]:
            self.assertTrue(rejected[word].startswith("flexion_basis:"))

    def test_rejects_capitalized_ens_case_forms_without_base(self):
        result = WordlistFilter().filter_lines(["Verfremdens", "Jubelchor"])
        accepted = {entry["word"] for entry in result["accepted"]}
        rejected = dict(result["rejected"])

        self.assertEqual(accepted, {"Jubelchor"})
        self.assertEqual(rejected["Verfremdens"], "flexion:ens")

    def test_rejects_place_names_and_derived_forms(self):
        result = WordlistFilter().filter_lines([
            "Prerow",
            "Prerower",
            "Prerows",
            "Prerowstrom",
            "Jubelchor",
        ])
        accepted = {entry["word"] for entry in result["accepted"]}
        rejected = dict(result["rejected"])

        self.assertEqual(accepted, {"Jubelchor"})
        self.assertEqual(rejected["Prerow"], "eigenname:ow")
        self.assertEqual(rejected["Prerower"], "eigenname_basis:Prerow")
        self.assertEqual(rejected["Prerows"], "flexion_basis:Prerow")
        self.assertEqual(rejected["Prerowstrom"], "eigenname_basis:Prerow")

    def test_rejects_configured_banned_place_forms(self):
        cfg = FilterConfig(banned_place_words=frozenset({"berlin"}))
        result = WordlistFilter(cfg).filter_lines(["Berlin", "Berliner", "Jubelchor"])
        accepted = {entry["word"] for entry in result["accepted"]}
        rejected = dict(result["rejected"])

        self.assertEqual(accepted, {"Jubelchor"})
        self.assertEqual(rejected["Berlin"], "ortsname:berlin")
        self.assertEqual(rejected["Berliner"], "ortsname:berlin")

    def test_rejects_configured_blocked_words(self):
        cfg = FilterConfig(blocked_words=frozenset({"neuroute", "seiher"}))
        result = WordlistFilter(cfg).filter_lines(["Neuroute", "Seiher", "Jubelchor"])
        accepted = {entry["word"] for entry in result["accepted"]}
        rejected = dict(result["rejected"])

        self.assertEqual(accepted, {"Jubelchor"})
        self.assertEqual(rejected["Neuroute"], "lokale_sperrliste")
        self.assertEqual(rejected["Seiher"], "lokale_sperrliste")

    def test_rejects_hard_sensitive_word_parts(self):
        cfg = FilterConfig(
            blocked_word_parts=frozenset({"nazi", "hitler", "hure", "neger"}),
            blocked_word_suffixes=frozenset({"sau"}),
        )
        result = WordlistFilter(cfg).filter_lines([
            "Nazidepp",
            "Hitlergruß",
            "Dreckshure",
            "Negerszene",
            "Pistensau",
            "Jubelchor",
        ])
        accepted = {entry["word"] for entry in result["accepted"]}
        rejected = dict(result["rejected"])

        self.assertEqual(accepted, {"Jubelchor"})
        self.assertEqual(rejected["Nazidepp"], "sensibler_bestandteil:nazi")
        self.assertEqual(rejected["Hitlergruß"], "sensibler_bestandteil:hitler")
        self.assertEqual(rejected["Dreckshure"], "sensibler_bestandteil:hure")
        self.assertEqual(rejected["Negerszene"], "sensibler_bestandteil:neger")
        self.assertEqual(rejected["Pistensau"], "sensibler_bestandteil:sau")

    def test_marks_curse_word_parts_without_rejecting_them(self):
        cfg = FilterConfig(
            adult_word_parts=frozenset({"fuck", "fick", "scheiß", "verdammt", "zefix"}),
        )
        result = WordlistFilter(cfg).filter_lines([
            "Fuckwort",
            "Verfickt",
            "Scheißwetter",
            "Verdammtgut",
            "Zefixruf",
            "Sauerstoff",
            "Jubelchor",
        ])
        accepted = {entry["word"]: entry for entry in result["accepted"]}

        self.assertEqual(set(accepted), {
            "Fuckwort", "Verfickt", "Scheißwetter", "Verdammtgut",
            "Zefixruf", "Sauerstoff", "Jubelchor",
        })
        self.assertTrue(accepted["Fuckwort"]["adult_only"])
        self.assertTrue(accepted["Verfickt"]["adult_only"])
        self.assertTrue(accepted["Scheißwetter"]["adult_only"])
        self.assertTrue(accepted["Verdammtgut"]["adult_only"])
        self.assertTrue(accepted["Zefixruf"]["adult_only"])
        self.assertFalse(accepted["Sauerstoff"]["adult_only"])
        self.assertFalse(accepted["Jubelchor"]["adult_only"])

    def test_normalizes_non_german_accents_but_preserves_umlauts(self):
        self.assertEqual(normalize_import_word("Attaché"), "Attache")
        self.assertEqual(normalize_import_word("Größe"), "Größe")

        result = WordlistFilter().filter_lines(["Attaché", "Größe"])
        accepted = {entry["word"] for entry in result["accepted"]}

        self.assertEqual(accepted, {"Attache", "Größe"})

    def test_marks_technical_terms_for_nerd_corner(self):
        cfg = FilterConfig(
            technical_word_parts=frozenset({"bundesamt", "geschlechtskrankheit"}),
            technical_case_sensitive_parts=frozenset({"BVerf"}),
        )
        result = WordlistFilter(cfg).filter_lines([
            "BVerfG",
            "Bundesamt",
            "Geschlechtskrankheit",
            "Jubelchor",
        ])
        accepted = {entry["word"]: entry for entry in result["accepted"]}

        self.assertTrue(accepted["BVerfG"]["is_technical"])
        self.assertTrue(accepted["Bundesamt"]["is_technical"])
        self.assertTrue(accepted["Geschlechtskrankheit"]["is_technical"])
        self.assertFalse(accepted["Jubelchor"]["is_technical"])

    def test_rejects_case_sensitive_parts_without_banning_lowercase_ss(self):
        cfg = FilterConfig(blocked_case_sensitive_parts=frozenset({"SS"}))
        result = WordlistFilter(cfg).filter_lines(["OpenSSL", "Masse", "Jubelchor"])
        accepted = {entry["word"] for entry in result["accepted"]}
        rejected = dict(result["rejected"])

        self.assertEqual(accepted, {"Masse", "Jubelchor"})
        self.assertEqual(rejected["OpenSSL"], "sensibler_bestandteil:SS")


if __name__ == "__main__":
    unittest.main()

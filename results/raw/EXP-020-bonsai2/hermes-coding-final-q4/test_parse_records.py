import unittest

from parse_records import parse_records


class TestParseRecords(unittest.TestCase):
    def test_valid_input(self):
        self.assertEqual(parse_records("a=1\nb=2\nc=3"), {"a": 1, "b": 2, "c": 3})

    def test_repeated_names_are_summed(self):
        self.assertEqual(parse_records("a=1\na=2\nb=5\na=-1"), {"a": 2, "b": 5})

    def test_whitespace_around_names_and_values(self):
        self.assertEqual(
            parse_records("  a  =  10  \n\n  b = 5 \n"), {"a": 10, "b": 5}
        )

    def test_empty_input_returns_empty_dict(self):
        self.assertEqual(parse_records(""), {})
        self.assertEqual(parse_records("\n\n"), {})

    def test_malformed_missing_equals(self):
        with self.assertRaises(ValueError):
            parse_records("noequals\na=1")

    def test_malformed_empty_name(self):
        with self.assertRaises(ValueError):
            parse_records("=5\na=1")

    def test_malformed_empty_value(self):
        with self.assertRaises(ValueError):
            parse_records("a=\nb=1")

    def test_malformed_non_integer_value(self):
        with self.assertRaises(ValueError):
            parse_records("a=abc\nb=1")

    def test_malformed_value_with_unequal_characters(self):
        with self.assertRaises(ValueError):
            parse_records("a=1=2")


if __name__ == "__main__":
    unittest.main()

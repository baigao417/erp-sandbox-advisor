import contextlib
import io
import unittest
from unittest.mock import patch

from erp_sandbox_advisor.__main__ import main, unique_object


class CliTests(unittest.TestCase):
    def test_duplicate_json_keys(self):
        with self.assertRaises(ValueError):
            unique_object([("a", 1), ("a", 2)])

    def test_help(self):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(["--help"])
        self.assertEqual(raised.exception.code, 0)

    def test_missing_file_does_not_echo_path(self):
        stderr = io.StringIO()
        with patch("pathlib.Path.read_text", side_effect=FileNotFoundError("private detail")), contextlib.redirect_stderr(stderr):
            self.assertEqual(main(["unused.json"]), 2)
        self.assertNotIn("private detail", stderr.getvalue())

    def test_malformed_json(self):
        with patch("pathlib.Path.read_text", return_value="{"), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["unused.json"]), 2)

    def test_invalid_structure(self):
        for text in ("[]", "null", "{}", '{"a": 1, "a": 2}'):
            with self.subTest(text=text), patch("pathlib.Path.read_text", return_value=text), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["unused.json"]), 2)


if __name__ == "__main__":
    unittest.main()

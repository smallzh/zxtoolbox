"""Tests for zxtoolbox.__init__ (cowsay function)."""

import pytest
from zxtoolbox import cowsay


class TestCowsay:
    """Test the cowsay ASCII art function."""

    def test_cowsay_single_word(self, capsys):
        """Test cowsay with a single word message."""
        cowsay("Hello")
        captured = capsys.readouterr()
        # cowsay joins with spaces: "H e l l o"
        assert "H e l l o" in captured.out
        assert "^__^" in captured.out
        assert "(oo)" in captured.out

    def test_cowsay_multiple_words(self, capsys):
        """Test cowsay joins multiple words with spaces."""
        cowsay(["Hello", "World"])
        captured = capsys.readouterr()
        assert "Hello World" in captured.out
        assert "^__^" in captured.out

    def test_cowsay_empty_string(self, capsys):
        """Test cowsay with empty string."""
        cowsay("")
        captured = capsys.readouterr()
        assert "^__^" in captured.out

    def test_cowsay_bar_length(self, capsys):
        """Test that the top/bottom bars match message length."""
        msg = "Test"
        cowsay(msg)
        captured = capsys.readouterr()
        assert "-" * len(msg) in captured.out

    def test_cowsay_long_message(self, capsys):
        """Test cowsay with a longer message."""
        msg = "This is a longer test message"
        cowsay(msg)
        captured = capsys.readouterr()
        # cowsay joins with spaces
        assert " ".join(msg) in captured.out
        assert "||----w |" in captured.out

    def test_cowsay_list_of_strings(self, capsys):
        """Test cowsay with a list of strings."""
        cowsay(["foo", "bar", "baz"])
        captured = capsys.readouterr()
        assert "foo bar baz" in captured.out

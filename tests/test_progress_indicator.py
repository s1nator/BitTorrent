import unittest
from io import StringIO
from unittest.mock import patch

from src.progress.indicator import ProgressIndicator


class TestProgressIndicator(unittest.TestCase):

    def test_initialization(self):

        indicator = ProgressIndicator(100, bar_length=50)
        self.assertEqual(indicator.total_pieces, 100)
        self.assertEqual(indicator.bar_length, 50)

    def test_update_zero_progress(self):

        indicator = ProgressIndicator(100, bar_length=10)
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            indicator.update(0)
            output = mock_stdout.getvalue()

        self.assertIn("0.00%", output)
        self.assertIn("[----------]", output)

    def test_update_full_progress(self):
        indicator = ProgressIndicator(100, bar_length=10)
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            indicator.update(100)
            output = mock_stdout.getvalue()

        self.assertIn("100.00%", output)
        self.assertIn("[##########]", output)

    def test_update_half_progress(self):
        indicator = ProgressIndicator(100, bar_length=10)
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            indicator.update(50)
            output = mock_stdout.getvalue()

        self.assertIn("50.00%", output)
        self.assertIn("#####", output)

    def test_update_zero_total_pieces(self):
        indicator = ProgressIndicator(0, bar_length=10)
        with patch('sys.stdout', new_callable=StringIO):
            indicator.update(0)

    def test_progress_bar_length_customization(self):
        """Test custom bar length"""
        indicator = ProgressIndicator(100, bar_length=20)
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            indicator.update(50)
            output = mock_stdout.getvalue()

        self.assertIn("##########----------", output)


class TestProgressIndicatorEdgeCases(unittest.TestCase):

    def test_single_piece(self):
        indicator = ProgressIndicator(1, bar_length=10)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            indicator.update(0)
            output = mock_stdout.getvalue()
        self.assertIn("0.00%", output)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            indicator.update(1)
            output = mock_stdout.getvalue()
        self.assertIn("100.00%", output)

    def test_progress_increments(self):
        indicator = ProgressIndicator(10, bar_length=10)
        outputs = []

        for i in range(11):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                indicator.update(i)
                outputs.append(mock_stdout.getvalue())

        self.assertIn("0.00%", outputs[0])
        self.assertIn("100.00%", outputs[10])


if __name__ == "__main__":
    unittest.main()

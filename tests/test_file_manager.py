import unittest
import tempfile
import shutil
import hashlib

from src.storage.file_manager import StorageManager


def get_piece_hashes(pieces):
    return b"".join(hashlib.sha1(p).digest() for p in pieces)


class TestStorageManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_single_file_torrent(self):
        piece_length = 8
        file_length = 24
        filename = "testfile.bin"
        torrent_info = {
            "name": filename,
            "length": file_length,
            "piece length": piece_length,
            "pieces": get_piece_hashes([b"abcdefgh", b"ijklmnop", b"qrstuvwx"]),
        }
        sm = StorageManager(torrent_info, self.tmp_dir)

        sm.write_piece(0, b"abcdefgh")
        sm.write_piece(1, b"ijklmnop")
        sm.write_piece(2, b"qrstuvwx")

        self.assertEqual(sm.read_piece(0, 0, 8), b"abcdefgh")
        self.assertEqual(sm.read_piece(1, 0, 8), b"ijklmnop")
        self.assertEqual(sm.read_piece(2, 0, 8), b"qrstuvwx")

        self.assertEqual(sm.read_piece(1, 2, 4), b"klmn")

        self.assertTrue(sm.piece_hash_valid(0, b"abcdefgh"))
        self.assertTrue(sm.piece_hash_valid(1, b"ijklmnop"))
        self.assertTrue(sm.piece_hash_valid(2, b"qrstuvwx"))
        self.assertFalse(sm.piece_hash_valid(0, b"12345678"))

    def test_multi_file_torrent_piece_spanning(self):
        piece_length = 8
        files = [{"length": 6, "path": ["f1"]}, {"length": 10, "path": ["f2"]}]

        piece0 = b"abcdefg1"
        piece1 = b"g2345678"
        torrent_info = {
            "files": files,
            "name": "parent",
            "piece length": piece_length,
            "pieces": get_piece_hashes([piece0, piece1]),
        }
        sm = StorageManager(torrent_info, self.tmp_dir)

        sm.write_piece(0, piece0)
        sm.write_piece(1, piece1)

        self.assertEqual(sm.read_piece(0, 0, 8), piece0)
        self.assertEqual(sm.read_piece(1, 0, 8), piece1)
        self.assertEqual(sm.read_piece(0, 6, 2), piece0[6:8])
        self.assertEqual(sm.read_piece(1, 4, 4), piece1[4:8])

        self.assertTrue(sm.piece_hash_valid(0, piece0))
        self.assertTrue(sm.piece_hash_valid(1, piece1))

    def test_write_and_read_piece_large_offset(self):
        piece_length = 16
        length = 40
        filename = "bigfile.bin"
        piece0 = b"a" * 16
        piece1 = b"b" * 16
        piece2 = b"abcd1234"

        torrent_info = {
            "name": filename,
            "length": length,
            "piece length": piece_length,
            "pieces": get_piece_hashes([piece0, piece1, piece2]),
        }
        sm = StorageManager(torrent_info, self.tmp_dir)
        sm.write_piece(2, piece2)
        self.assertEqual(sm.read_piece(2, 0, 8), b"abcd1234")
        self.assertTrue(sm.piece_hash_valid(2, piece2))


if __name__ == "__main__":
    unittest.main()

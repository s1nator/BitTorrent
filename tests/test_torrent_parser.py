import unittest
import tempfile
import os
import hashlib
import bcoding

from src.torrent.parser import TorrentFileParser


class TestTorrentFileParser(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        for f in os.listdir(self.tmp_dir):
            os.remove(os.path.join(self.tmp_dir, f))
        os.rmdir(self.tmp_dir)

    def _create_torrent_file(self, torrent_data: dict) -> str:

        path = os.path.join(self.tmp_dir, "test.torrent")
        with open(path, "wb") as f:
            f.write(bcoding.bencode(torrent_data))
        return path

    def test_parse_single_file_torrent(self):
        info = {
            "name": "testfile.txt",
            "length": 1024,
            "piece length": 256,
            "pieces": b"\x00" * 80,
        }
        torrent_data = {
            "announce": "http://example.com/announce",
            "info": info,
        }

        torrent_path = self._create_torrent_file(torrent_data)
        parser = TorrentFileParser(torrent_path, self.tmp_dir)
        result = parser.parse()

        self.assertIsNotNone(result)
        trackers, info_hash, peer_id, left, parsed_info = result

        self.assertEqual(trackers, ["http://example.com/announce"])
        self.assertEqual(left, 1024)
        self.assertEqual(parsed_info["name"], "testfile.txt")
        self.assertEqual(len(info_hash), 20)
        self.assertTrue(peer_id.startswith(b"-PC0001-"))

    def test_parse_multi_file_torrent(self):
        info = {
            "name": "test_folder",
            "piece length": 512,
            "pieces": b"\x00" * 40,
            "files": [
                {"length": 500, "path": ["file1.txt"]},
                {"length": 300, "path": ["subdir", "file2.txt"]},
            ],
        }
        torrent_data = {
            "announce": "http://example.com/announce",
            "announce-list": [
                ["http://example1.com/announce"],
                ["udp://example2.com:6969"],
            ],
            "info": info,
        }

        torrent_path = self._create_torrent_file(torrent_data)
        parser = TorrentFileParser(torrent_path, self.tmp_dir)
        result = parser.parse()

        self.assertIsNotNone(result)
        trackers, info_hash, peer_id, left, parsed_info = result

        self.assertIn("http://example1.com/announce", trackers)
        self.assertIn("udp://example2.com:6969", trackers)
        self.assertEqual(left, 800)

    def test_get_total_size_single_file(self):
        """Test total size calculation for single file"""
        info = {"length": 2048, "name": "file.bin"}
        parser = TorrentFileParser("abc", "abc")
        self.assertEqual(parser.get_total_size(info), 2048)

    def test_get_total_size_multi_file(self):
        info = {
            "files": [
                {"length": 100, "path": ["a.txt"]},
                {"length": 200, "path": ["b.txt"]},
                {"length": 300, "path": ["c.txt"]},
            ]
        }
        parser = TorrentFileParser("dummy", "dummy")
        self.assertEqual(parser.get_total_size(info), 600)

    def test_info_hash_consistency(self):

        info = {
            "name": "test.txt",
            "length": 512,
            "piece length": 256,
            "pieces": b"\x00" * 40,
        }
        torrent_data = {"announce": "http://example.com", "info": info}

        torrent_path = self._create_torrent_file(torrent_data)
        parser = TorrentFileParser(torrent_path, self.tmp_dir)
        result = parser.parse()

        expected_hash = hashlib.sha1(bcoding.bencode(info)).digest()
        self.assertEqual(result[1], expected_hash)


if __name__ == "__main__":
    unittest.main()

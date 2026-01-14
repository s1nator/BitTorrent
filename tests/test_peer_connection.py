import unittest
import struct
import socket
import threading
import hashlib
from unittest.mock import Mock, MagicMock, patch

from src.peer.connection import PeerConnection


class MockStorageManager:

    def __init__(self, total_pieces=10, piece_length=16384):
        self.total_pieces = total_pieces
        self.piece_length = piece_length
        self.pieces_status = [False] * total_pieces
        self.torrent_info = {
            "pieces": b"\x00" * (total_pieces * 20),
            "piece length": piece_length,
            "length": total_pieces * piece_length,
        }

    def get_bitfield(self):
        import math
        num_bytes = math.ceil(self.total_pieces / 8)
        bitfield = bytearray(num_bytes)
        for i, has_piece in enumerate(self.pieces_status):
            if has_piece:
                byte_index = i // 8
                bit_index = i % 8
                bitfield[byte_index] |= 1 << (7 - bit_index)
        return bytes(bitfield)

    def read_piece(self, piece_index, offset, length):
        return b"\x00" * length

    def write_piece(self, piece_index, data):
        pass

    def mark_piece_completed(self, piece_index):
        self.pieces_status[piece_index] = True

    def piece_hash_valid(self, piece_index, data):
        return True


class TestPeerConnectionMessages(unittest.TestCase):

    def setUp(self):
        self.mock_socket = Mock(spec=socket.socket)
        self.info_hash = b"\x00" * 20
        self.peer_id = b"-PC0001-123456789012"
        self.storage = MockStorageManager()

        with patch.object(PeerConnection, '__init__', lambda x, *args: None):
            self.conn = PeerConnection.__new__(PeerConnection)
            self.conn.peer_socket = self.mock_socket
            self.conn.info_hash = self.info_hash
            self.conn.peer_id = self.peer_id
            self.conn.storage_manager = self.storage
            self.conn.running = True
            self.conn.am_interested = False
            self.conn.peer_choking = True
            self.conn.peer_pieces = [False] * self.storage.total_pieces
            self.conn.current_piece_index = -1
            self.conn.current_piece_buffer = bytearray()
            self.conn.current_piece_downloaded = 0
            self.conn.block_size = 16384
            self.conn._lock = threading.Lock()

    def test_process_choke_message(self):
        self.conn.peer_choking = False
        self.conn.process_message(0, b"")
        self.assertTrue(self.conn.peer_choking)

    def test_process_unchoke_message(self):
        self.conn.peer_choking = True
        self.conn.process_message(1, b"")
        self.assertFalse(self.conn.peer_choking)

    def test_process_have_message(self):
        piece_index = 5
        payload = struct.pack(">I", piece_index)
        self.conn.process_message(4, payload)
        self.assertTrue(self.conn.peer_pieces[5])
        self.assertFalse(self.conn.peer_pieces[0])

    def test_process_bitfield_message(self):
        bitfield = bytes([0xC1, 0x00])
        self.conn.process_bitfield(bitfield)
        self.assertTrue(self.conn.peer_pieces[0])
        self.assertTrue(self.conn.peer_pieces[1])
        self.assertFalse(self.conn.peer_pieces[2])
        self.assertTrue(self.conn.peer_pieces[7])
        self.assertFalse(self.conn.peer_pieces[8])


class TestPeerConnectionHandshake(unittest.TestCase):

    def test_handshake_packet_structure(self):
        """Test that handshake packet is constructed correctly"""
        protocol = b"BitTorrent protocol"
        info_hash = b"A" * 20
        peer_id = b"-PC0001-123456789012"

        protocol_len = len(protocol)
        reserved = b"\x00" * 8
        packet = struct.pack(
            f">B{protocol_len}s8s20s20s",
            protocol_len,
            protocol,
            reserved,
            info_hash,
            peer_id,
        )

        self.assertEqual(len(packet), 1 + 19 + 8 + 20 + 20)  # 68 bytes
        self.assertEqual(packet[0], 19)
        self.assertEqual(packet[1:20], protocol)
        self.assertEqual(packet[20:28], reserved)
        self.assertEqual(packet[28:48], info_hash)
        self.assertEqual(packet[48:68], peer_id)

    def test_parse_request_message(self):
        mock_socket = Mock()
        storage = MockStorageManager()

        with patch.object(PeerConnection, '__init__', lambda x, *args: None):
            conn = PeerConnection.__new__(PeerConnection)
            conn.peer_socket = mock_socket
            conn.storage_manager = storage

        piece_index = 5
        begin = 16384
        length = 8192
        payload = struct.pack(">III", piece_index, begin, length)

        result = conn.parse_request(payload)
        self.assertEqual(result, (5, 16384, 8192))


class TestBitfieldEncoding(unittest.TestCase):

    def test_get_bitfield_empty(self):
        storage = MockStorageManager(total_pieces=16)
        bitfield = storage.get_bitfield()
        self.assertEqual(bitfield, bytes([0x00, 0x00]))

    def test_get_bitfield_all_complete(self):

        storage = MockStorageManager(total_pieces=8)
        storage.pieces_status = [True] * 8
        bitfield = storage.get_bitfield()
        self.assertEqual(bitfield, bytes([0xFF]))

    def test_get_bitfield_partial(self):

        storage = MockStorageManager(total_pieces=8)
        storage.pieces_status = [True, False,
                                 True, False, False, False, False, True]
        bitfield = storage.get_bitfield()
        self.assertEqual(bitfield, bytes([0xA1]))


if __name__ == "__main__":
    unittest.main()

import struct
import threading
import logging

logger = logging.getLogger(__name__)


class PeerConnection(threading.Thread):
    """
    Handles a peer connection: handshake, message parsing, and seeding
    """

    def __init__(self, peer_socket, info_hash, peer_id, storage_manager):
        """
        Args:
            peer_socket (socket.socket): The socket connected to the peer
            info_hash (bytes): 20-byte info_hash from the .torrent file
            peer_id (bytes): 20-byte peer ID for this client
            storage_manager (StorageManager): For reading pieces from disk
        """
        super().__init__()
        self.peer_socket = peer_socket
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.storage_manager = storage_manager
        self.running = True

    def run(self):
        if self.perform_handshake():
            self.send_bitfield()
            self.handle_peer_session()
        self.peer_socket.close()

    def perform_handshake(self):
        """
        Perform the BitTorrent handshake

        Returns:
            bool: True if handshake is successful
        """
        try:
            protocol = b"BitTorrent protocol"
            protocol_len = len(protocol)
            reserved = b"\x00" * 8

            packet = struct.pack(
                f">B{protocol_len}s8s20s20s",
                protocol_len,
                protocol,
                reserved,
                self.info_hash,
                self.peer_id,
            )
            self.peer_socket.sendall(packet)

            response = self._recvall(49 + protocol_len)
            if not response or len(response) < 49 + protocol_len:
                logger.error("Handshake failed: incomplete response")
                return False

            recv_protocol_len = response[0]
            recv_protocol = response[1 : 1 + recv_protocol_len]
            recv_info_hash = response[
                1 + recv_protocol_len + 8 : 1 + recv_protocol_len + 8 + 20
            ]

            if recv_protocol != protocol:
                logger.error("Handshake failed: protocol mismatch")
                return False
            if recv_info_hash != self.info_hash:
                logger.error("Handshake failed: info_hash mismatch")
                return False

            logger.info("Handshake with peer succeeded")
            return True
        except Exception as e:
            logger.error(f"Handshake error: {e}")
            return False

    def handle_peer_session(self):
        """
        Main message handling loop: respond to 'request' messages with piece data
        """
        try:
            while self.running:
                msg_id, payload = self.recv_bt_message()
                if msg_id is None:
                    break

                if msg_id == 2:
                    logger.info("Peer is interested, unchoking")
                    self.send_unchoke()

                if msg_id == 6:
                    piece_index, begin, length = self.parse_request(payload)
                    block = self.storage_manager.read_piece(piece_index, begin, length)
                    self.send_piece(piece_index, begin, block)
        except Exception as e:
            logger.error(f"Peer session error: {e}")

    def stop(self):
        self.running = False
        self.peer_socket.close()

    def recv_bt_message(self):
        length_bytes = self._recvall(4)
        if not length_bytes:
            return None, None
        length = struct.unpack(">I", length_bytes)[0]
        if length == 0:
            return 0, None
        msg = self._recvall(length)
        if not msg:
            return None, None
        msg_id = msg[0]
        payload = msg[1:]
        return msg_id, payload

    def _recvall(self, n):
        data = bytearray()
        while len(data) < n:
            chunk = self.peer_socket.recv(n - len(data))
            if not chunk:
                return None
            data.extend(chunk)
        return bytes(data)

    def parse_request(self, payload):
        return struct.unpack(">III", payload)

    def send_piece(self, piece_index, begin, block):
        msg_len = 1 + 4 + 4 + len(block)
        msg = struct.pack(">IBII", msg_len, 7, piece_index, begin) + block
        self.peer_socket.sendall(msg)

    def send_unchoke(self):
        msg = struct.pack(">IB", 1, 1)
        self.peer_socket.sendall(msg)

    def send_bitfield(self):
        bitfield = self.storage_manager.get_bitfield()
        msg_len = 1 + len(bitfield)
        msg = struct.pack(f">IB{len(bitfield)}s", msg_len, 5, bitfield)
        self.peer_socket.sendall(msg)

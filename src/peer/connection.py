import struct
import threading
import logging
import math
import time

logger = logging.getLogger(__name__)


class PeerConnection(threading.Thread):

    def __init__(self, peer_socket, info_hash, peer_id, storage_manager):
        super().__init__()
        self.peer_socket = peer_socket
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.storage_manager = storage_manager
        self.running = True

        self.am_interested = False
        self.peer_choking = True
        self.peer_pieces = [False] * self.storage_manager.total_pieces
        self.current_piece_index = -1
        self.current_piece_buffer = bytearray()
        self.current_piece_downloaded = 0
        self.block_size = 16384

    def run(self):
        if self.perform_handshake():
            self.send_bitfield()
            self.send_interested()
            self.handle_peer_session()
        self.peer_socket.close()

    def perform_handshake(self):
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
        try:
            while self.running:
                if (
                    not self.peer_choking
                    and self.current_piece_index == -1
                    and not all(self.storage_manager.pieces_status)
                ):
                    self.request_next_piece()

                self.peer_socket.settimeout(0.1)
                try:
                    msg_id, payload = self.recv_bt_message()
                except TimeoutError:
                    continue
                except Exception as e:
                    if not self.running:
                        break
                    continue

                if msg_id is None:
                    break

                self.process_message(msg_id, payload)

        except Exception as e:
            logger.error(f"Peer session error: {e}")

    def process_message(self, msg_id, payload):
        if msg_id == -1:
            return
        if msg_id == 0:
            logger.info("Peer choked us")
            self.peer_choking = True
        elif msg_id == 1:
            logger.info("Peer unchoked us")
            self.peer_choking = False
        elif msg_id == 2:
            logger.info("Peer is interested")
            self.send_unchoke()
        elif msg_id == 3:
            pass
        elif msg_id == 4:
            piece_index = struct.unpack(">I", payload)[0]
            if piece_index < len(self.peer_pieces):
                self.peer_pieces[piece_index] = True
        elif msg_id == 5:
            self.process_bitfield(payload)
        elif msg_id == 6:
            piece_index, begin, length = self.parse_request(payload)
            block = self.storage_manager.read_piece(piece_index, begin, length)
            self.send_piece(piece_index, begin, block)
        elif msg_id == 7:
            self.process_piece(payload)

    def process_bitfield(self, payload):
        for i, byte in enumerate(payload):
            for j in range(8):
                if i * 8 + j < len(self.peer_pieces):
                    if (byte >> (7 - j)) & 1:
                        self.peer_pieces[i * 8 + j] = True

    def request_next_piece(self):
        for i in range(self.storage_manager.total_pieces):
            if not self.storage_manager.pieces_status[i] and self.peer_pieces[i]:
                self.current_piece_index = i
                self.current_piece_downloaded = 0
                self.current_piece_buffer = bytearray()
                logger.info(f"Starting to download piece {i}")
                self.request_next_block()
                return

        if not any(
            not self.storage_manager.pieces_status[i] and self.peer_pieces[i]
            for i in range(self.storage_manager.total_pieces)
        ):
            logger.info("Peer doesn't have any pieces we need")
            time.sleep(1)

    def request_next_block(self):
        if self.current_piece_index == -1:
            return

        piece_length = self.storage_manager.piece_length
        if self.current_piece_index == self.storage_manager.total_pieces - 1:
            total_length = 0
            if "files" in self.storage_manager.torrent_info:
                total_length = sum(
                    f["length"] for f in self.storage_manager.torrent_info["files"]
                )
            else:
                total_length = self.storage_manager.torrent_info["length"]
            piece_length = total_length % self.storage_manager.piece_length
            if piece_length == 0:
                piece_length = self.storage_manager.piece_length

        if self.current_piece_downloaded >= piece_length:
            self.verify_and_write_piece()
            return

        begin = self.current_piece_downloaded
        length = min(self.block_size, piece_length - begin)

        msg = struct.pack(">IBIII", 13, 6, self.current_piece_index, begin, length)
        self.peer_socket.sendall(msg)

    def process_piece(self, payload):
        piece_index = struct.unpack(">I", payload[:4])[0]
        begin = struct.unpack(">I", payload[4:8])[0]
        block = payload[8:]

        if piece_index != self.current_piece_index:
            logger.warning(
                f"Received block for piece {piece_index} but expected {self.current_piece_index}"
            )
            return

        if begin != self.current_piece_downloaded:
            logger.warning(
                f"Received block at offset {begin} but expected {self.current_piece_downloaded}"
            )
            return

        self.current_piece_buffer.extend(block)
        self.current_piece_downloaded += len(block)

        self.request_next_block()

    def verify_and_write_piece(self):
        data = bytes(self.current_piece_buffer)
        if self.storage_manager.piece_hash_valid(self.current_piece_index, data):
            self.storage_manager.write_piece(self.current_piece_index, data)
            self.storage_manager.mark_piece_completed(self.current_piece_index)
            logger.info(f"Piece {self.current_piece_index} verified and written")
        else:
            logger.error(f"Piece {self.current_piece_index} hash check failed")

        self.current_piece_index = -1
        self.current_piece_buffer = bytearray()
        self.current_piece_downloaded = 0

    def stop(self):
        self.running = False
        self.peer_socket.close()

    def recv_bt_message(self):
        length_bytes = self._recvall(4)
        if not length_bytes:
            return None, None
        length = struct.unpack(">I", length_bytes)[0]
        if length == 0:
            return -1, None  # Keep-alive
        msg = self._recvall(length)
        if not msg:
            return None, None
        msg_id = msg[0]
        payload = msg[1:]
        return msg_id, payload

    def _recvall(self, n):
        data = bytearray()
        while len(data) < n:
            try:
                chunk = self.peer_socket.recv(n - len(data))
                if not chunk:
                    return None
                data.extend(chunk)
            except TimeoutError:
                raise
            except Exception:
                return None
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

    def send_interested(self):
        msg = struct.pack(">IB", 1, 2)
        self.peer_socket.sendall(msg)

    def send_bitfield(self):
        bitfield = self.storage_manager.get_bitfield()
        msg_len = 1 + len(bitfield)
        msg = struct.pack(f">IB{len(bitfield)}s", msg_len, 5, bitfield)
        self.peer_socket.sendall(msg)

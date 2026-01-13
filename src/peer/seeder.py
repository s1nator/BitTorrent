import socket
import struct
import threading
import logging

from src import state

logger = logging.getLogger(__name__)


class SeederServer:
    """Server that listens for incoming peer connections and seeds files"""

    def __init__(
        self, info_hash: bytes, peer_id: bytes, storage_manager, port: int = 6889
    ):
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.storage_manager = storage_manager
        self.port = port
        self.server_socket = None
        self.running = False
        self.connections = []
        self._lock = threading.Lock()

    def start(self):
        """Start the seeder server (new thread)"""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind(("0.0.0.0", self.port))
            self.server_socket.listen(10)
            self.server_socket.settimeout(1.0)
            logger.info(f"Seeder listening on port {self.port}")
            print(f"\n🌱 Seeding on port {self.port}")

            while self.running and not state.is_stopped():
                try:
                    client_sock, addr = self.server_socket.accept()
                    logger.info(f"Incoming connection from {addr[0]}:{addr[1]}")
                    handler = threading.Thread(
                        target=self._handle_incoming,
                        args=(client_sock, addr),
                        daemon=True,
                    )
                    handler.start()
                    with self._lock:
                        self.connections.append(handler)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Accept error: {e}")
                    break
        except OSError as e:
            logger.error(f"Failed to bind to port {self.port}: {e}")
        finally:
            self.stop()

    def _handle_incoming(self, client_sock: socket.socket, addr: tuple):
        """Handle an incoming peer connection"""
        client_sock.settimeout(30)
        try:
            if not self._recv_handshake(client_sock):
                client_sock.close()
                return

            self._send_handshake(client_sock)
            self._send_bitfield(client_sock)
            self._handle_requests(client_sock, addr)

        except Exception as e:
            logger.error(f"Error handling peer {addr}: {e}")
        finally:
            try:
                client_sock.close()
            except Exception:
                pass

    def _recv_handshake(self, sock: socket.socket) -> bool:
        """Receive and validate incoming handshake"""
        try:
            pstrlen_bytes = self._recvall(sock, 1)
            if not pstrlen_bytes:
                return False
            pstrlen = pstrlen_bytes[0]

            remaining = self._recvall(sock, pstrlen + 8 + 20 + 20)
            if not remaining or len(remaining) < pstrlen + 48:
                return False

            pstr = remaining[:pstrlen]
            recv_info_hash = remaining[pstrlen + 8 : pstrlen + 8 + 20]

            if pstr != b"BitTorrent protocol":
                logger.warning("Invalid protocol in handshake")
                return False

            if recv_info_hash != self.info_hash:
                logger.warning("Info hash mismatch in handshake")
                return False

            logger.info("Received valid handshake from peer")
            return True

        except Exception as e:
            logger.error(f"Handshake receive error: {e}")
            return False

    def _send_handshake(self, sock: socket.socket):
        """Send handshake response"""
        protocol = b"BitTorrent protocol"
        packet = struct.pack(
            f">B{len(protocol)}s8s20s20s",
            len(protocol),
            protocol,
            b"\x00" * 8,
            self.info_hash,
            self.peer_id,
        )
        sock.sendall(packet)
        logger.info("Sent handshake to peer")

    def _send_bitfield(self, sock: socket.socket):
        """Send our bitfield to the peer"""
        bitfield = self.storage_manager.get_bitfield()
        msg_len = 1 + len(bitfield)
        msg = struct.pack(f">IB{len(bitfield)}s", msg_len, 5, bitfield)
        sock.sendall(msg)
        logger.info("Sent bitfield to peer")

    def _handle_requests(self, sock: socket.socket, addr: tuple):
        """Handle piece requests from the peer."""
        # Unchoke
        sock.sendall(struct.pack(">IB", 1, 1))
        logger.info(f"Sent unchoke to {addr}")

        while self.running and not state.is_stopped():
            try:
                len_bytes = self._recvall(sock, 4)
                if not len_bytes:
                    break

                msg_len = struct.unpack(">I", len_bytes)[0]
                if msg_len == 0:
                    continue

                msg = self._recvall(sock, msg_len)
                if not msg:
                    break

                msg_id = msg[0]
                payload = msg[1:]

                if msg_id == 2:
                    logger.info(f"Peer {addr} is interested")
                    # Unchoke
                    sock.sendall(struct.pack(">IB", 1, 1))

                elif msg_id == 6:
                    piece_index, begin, length = struct.unpack(">III", payload)
                    logger.info(
                        f"Request from {addr}: piece={piece_index}, begin={begin}, length={length}"
                    )

                    block = self.storage_manager.read_piece(piece_index, begin, length)

                    piece_msg_len = 1 + 4 + 4 + len(block)
                    piece_msg = (
                        struct.pack(">IBII", piece_msg_len, 7, piece_index, begin)
                        + block
                    )
                    sock.sendall(piece_msg)
                    logger.info(
                        f"Sent block to {addr}: piece={piece_index}, begin={begin}, length={len(block)}"
                    )

                elif msg_id == 3:
                    logger.info(f"Peer {addr} is not interested")
                    break

            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error handling request from {addr}: {e}")
                break

    def _recvall(self, sock: socket.socket, n: int) -> bytes | None:
        """Receive exactly n bytes"""
        data = bytearray()
        while len(data) < n:
            try:
                chunk = sock.recv(n - len(data))
                if not chunk:
                    return None
                data.extend(chunk)
            except socket.timeout:
                continue
            except Exception:
                return None
        return bytes(data)

    def stop(self):
        """Stop the seeder server"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        logger.info("Seeder server stopped")

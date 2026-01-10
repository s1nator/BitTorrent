from src.peer.connection import PeerConnection
from src.tracker.get_peers import GetPeers
from src.torrent.parser import TorrentFileParser
from src.storage.file_manager import StorageManager
import struct
import logging
import socket


class HandShakeTCP:
    source: str
    destination: str
    logger = logging.getLogger(__name__)

    def __init__(self, source: str, destination: str) -> None:
        self.source = source
        self.destination = destination

    def handshake(self) -> None:
        list_args, info_hash, peer_id, left, torrent_info = TorrentFileParser(
            self.source, self.destination
        ).parse()
        peers, info_h, peer_id = GetPeers(self.source, self.destination).peers()
        protocol = "BitTorrent protocol".encode("utf-8")
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

        storage = StorageManager(torrent_info, self.destination)

        while not all(storage.pieces_status):
            connected = False
            for peer in peers:
                if all(storage.pieces_status):
                    break

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                try:
                    logging.info(f"Connecting to {peer[0]}:{peer[1]}")
                    sock.connect(peer)
                    sock.sendall(packet)
                    response = sock.recv(1024)
                    if not response:
                        logging.error("Peer closed connection")
                        sock.close()
                        continue

                    if len(response) < 16:
                        logging.error("Peer is small")
                        sock.close()
                        continue

                    protocol_len = response[0]
                    received_protocol = response[1 : 1 + protocol_len]

                    logging.info(
                        f"Connecting successful protocol: {received_protocol.decode('utf-8', errors='ignore')}"
                    )
                    peer_connection = PeerConnection(sock, info_hash, peer_id, storage)
                    peer_connection.start()
                    peer_connection.join()
                    sock.close()
                    connected = True
                    if all(storage.pieces_status):
                        break

                except Exception as e:
                    logging.error(f"Error connecting to {peer[0]}:{peer[1]}: {e}")
                    sock.close()

            if not connected and not all(storage.pieces_status):
                logging.error(
                    "Could not connect to any peer or download incomplete. Retrying..."
                )
                import time

                time.sleep(5)
            elif all(storage.pieces_status):
                logging.info("Download complete!")
                break

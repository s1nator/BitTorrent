from src.peer.connection import PeerConnection
from src.peer.seeder import SeederServer
from src.tracker.get_peers import GetPeers
from src.torrent.parser import TorrentFileParser
from src.storage.file_manager import StorageManager
from src import state
import logging
import socket
import threading
import time


class HandShakeTCP:
    source: str
    destination: str
    logger = logging.getLogger(__name__)

    def __init__(self, source: str, destination: str, seed: bool = True) -> None:
        self.source = source
        self.destination = destination
        self.seed = seed
        self.seeder = None

    def handshake(self) -> None:
        parse_result = TorrentFileParser(self.source, self.destination).parse()
        if parse_result is None:
            logging.error("Failed to parse torrent file")
            return

        _, info_hash, peer_id, _, torrent_info = parse_result
        peers, _, _ = GetPeers(self.source, self.destination).peers()

        if peers is None:
            logging.error("Failed to get peers from tracker")
            return

        storage = StorageManager(torrent_info, self.destination)

        if self.seed:
            self.seeder = SeederServer(info_hash, peer_id, storage)
            seeder_thread = threading.Thread(target=self.seeder.start, daemon=True)
            seeder_thread.start()

        while not all(storage.pieces_status):
            if state.is_stopped():
                logging.info("Download stopped by user")
                self._stop_seeder()
                return
            if not state.wait_if_paused():
                self._stop_seeder()
                return

            connected = False
            for peer in peers:
                if state.is_stopped():
                    self._stop_seeder()
                    return
                if all(storage.pieces_status):
                    break

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                try:
                    logging.info(f"Connecting to {peer[0]}:{peer[1]}")
                    sock.connect(peer)
                    # PeerConnection handles the handshake
                    peer_connection = PeerConnection(sock, info_hash, peer_id, storage)
                    peer_connection.start()
                    peer_connection.join()
                    # Socket closed by PeerConnection.run()
                    connected = True
                    if all(storage.pieces_status):
                        break

                except Exception as e:
                    logging.error(f"Error connecting to {peer[0]}:{peer[1]}: {e}")
                    try:
                        sock.close()
                    except Exception:
                        pass

            if not connected and not all(storage.pieces_status):
                if state.is_stopped():
                    self._stop_seeder()
                    return
                logging.error(
                    "Could not connect to any peer or download incomplete. Retrying..."
                )
                time.sleep(5)
            elif all(storage.pieces_status):
                logging.info("Download complete!")
                break

        if self.seed and self.seeder:
            print("\nDownload complete! Seeding... (press 'q' to stop)")
            while not state.is_stopped():
                if not state.wait_if_paused():
                    break
                time.sleep(1)
            self._stop_seeder()

    def _stop_seeder(self):
        """Stop the seeder server if running"""
        if self.seeder:
            self.seeder.stop()
            self.seeder = None

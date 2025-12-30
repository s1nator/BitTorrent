from src.tracker.get_peers import GetPeers
from src.torrent.parser import TorrentFileParser
import struct
import socket


class HandShakeTCP:
    source: str
    destination: str

    def __init__(self, source: str, destination: str) -> None:
        self.source = source
        self.destination = destination

    def handshake(self) -> None:
        list_args, info_hash, peer_id, left = TorrentFileParser(
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

        for peer in peers:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            try:
                print(f"Connecting to {peer[0]}:{peer[1]}")
                sock.connect(peer)
                sock.sendall(packet)
                response = sock.recv(1024)
                if not response:
                    print("Peer closed connection")
                    continue

                if len(response) < 16:
                    print("Peer is small")
                    continue

                protocol_len = response[0]
                received_protocol = response[1 : 1 + protocol_len]

                print(
                    f"Connecting successfull protocol: {received_protocol.decode('utf-8', errors='ignore')}"
                )
                break

            except Exception as e:
                print(f"Error connecting to {peer[0]}:{peer[1]}: {e}")

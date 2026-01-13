from src.torrent.parser import TorrentFileParser
import bcoding
import requests
import socket
import struct
import random
import logging

logger = logging.getLogger(__name__)


class GetPeers:
    source: str
    destination: str

    def __init__(self, source: str, destination: str) -> None:
        self.source = source
        self.destination = destination

    def peers(self) -> tuple[list[str], int, bytes] | tuple[None, None, None]:
        parser = TorrentFileParser(self.source, self.destination)
        list_args = parser.parse()

        params = {
            "info_hash": list_args[1],
            "peer_id": list_args[2],
            "uploaded": 0,
            "downloaded": 0,
            "left": list_args[3],
            "port": 6889,
            "compact": 1,
        }

        for index in list_args[0]:
            if "http" in index or "https" in index:
                try:
                    response = requests.get(index, params=params, timeout=5)
                    if response.status_code == 200:
                        tracker_response = bcoding.bdecode(response.content)
                        if "peers" in tracker_response:
                            peers_data = tracker_response["peers"]
                            peers = []
                            if isinstance(peers_data, bytes):
                                # Compact format
                                for i in range(0, len(peers_data), 6):
                                    ip_bytes = peers_data[i:i+4]
                                    port_bytes = peers_data[i+4:i+6]
                                    ip_str = socket.inet_ntoa(ip_bytes)
                                    port_int = struct.unpack(
                                        "!H", port_bytes)[0]
                                    peers.append((ip_str, port_int))
                            else:
                                # Dictionary format
                                for peer in peers_data:
                                    peers.append((peer["ip"], peer["port"]))
                            if peers:
                                logger.info(
                                    f"Found {len(peers)} peers from HTTP tracker {index}")
                                return peers, list_args[1], list_args[2]
                except Exception as e:
                    logger.error(f"HTTP tracker error: {e}")
                    continue
            else:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.settimeout(5)
                    domain_name = index.split(":")
                    domain_name = domain_name[1][2:]
                    port = index.split(":")[2].split("/")[0]
                    server_address = (str(domain_name), int(port))
                    protocol_id = 0x41727101980
                    action_connect = 0
                    transaction_id = random.randint(0, 2**32 - 1)

                    connect_packed = struct.pack(
                        "!QII", protocol_id, action_connect, transaction_id
                    )
                    sock.sendto(connect_packed, server_address)

                    response, _ = sock.recvfrom(10000)

                    if len(response) < 16:
                        logger.error(f"Error bad response from {index}")
                        continue

                    action, response_transaction_id, connection_id = struct.unpack(
                        "!IIQ", response[:16]
                    )

                    if response_transaction_id != transaction_id:
                        logger.error(f"Wrong transaction id from {index}")
                        continue

                    action_announce = 1
                    event = 0
                    ip = 0
                    key = random.randint(0, 2**32 - 1)
                    num_want = -1
                    for param_key, value in params.items():
                        if param_key == "peer_id":
                            peer_id = value.encode("utf-8")
                        if param_key == "info_hash":
                            info_hash = value
                        if param_key == "downloaded":
                            downloaded = int(value)
                        if param_key == "uploaded":
                            uploaded = int(value)
                        if param_key == "left":
                            left = int(value)
                        if param_key == "port":
                            port_for_request = int(value)

                    announce_packet = struct.pack(
                        "!QII20s20sQQQIIIiH",
                        connection_id,
                        action_announce,
                        transaction_id,
                        info_hash,
                        peer_id,
                        downloaded,
                        left,
                        uploaded,
                        event,
                        ip,
                        key,
                        num_want,
                        port_for_request,
                    )

                    sock.sendto(announce_packet, server_address)

                    response, _ = sock.recvfrom(10000)

                    if len(response) < 20:
                        logger.error(
                            f"Response is smaller than 20 from {index}")
                        continue

                    peers_ip = response[20:]

                    peers = []
                    for i in range(0, len(peers_ip), 6):
                        ip_bites = peers_ip[i: i + 4]
                        port_bytes = peers_ip[i + 4: i + 6]

                        ip_str = socket.inet_ntoa(ip_bites)
                        port_int = struct.unpack("!H", port_bytes)[0]
                        peers.append((ip_str, int(port_int)))

                    logger.info(f"Found {len(peers)} peers from {index}")
                    sock.close()
                    return peers, info_hash, peer_id

                except Exception as e:
                    logger.error(f"Error connecting to tracker {index}: {e}")
                    try:
                        sock.close()
                    except Exception:
                        pass
                    continue

        return None, None, None

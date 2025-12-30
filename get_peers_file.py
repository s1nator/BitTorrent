from torrent_file_parser import TorrentFileParser
import requests
import socket
import struct
import random


class GetPeers:
    source: str
    destination: str

    def __init__(self, source, destination) -> None:
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
                request = requests.get(index, params=params).status_code
            else:
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
                try:
                    response, _ = sock.recvfrom(10000)
                except Exception as e:
                    raise Exception(f"Error: {e}")

                if len(response) < 16:
                    raise Exception(f"Error bad response")

                action, response_transaction_id, connection_id = struct.unpack(
                    "!IIQ", response[:16]
                )

                if response_transaction_id != transaction_id:
                    raise Exception("Wrong transaction id")

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

                try:
                    response, _ = sock.recvfrom(10000)
                except Exception as e:
                    raise Exception(f"Error: {e}")

                if len(response) < 20:
                    raise Exception(f"response is smaller than 20")

                peers_ip = response[20:]

                peers = []
                for index in range(0, len(peers_ip), 6):
                    ip_bites = peers_ip[index : index + 4]
                    port_bytes = peers_ip[index + 4 : index + 6]

                    ip_str = socket.inet_ntoa(ip_bites)
                    port_int = struct.unpack("!H", port_bytes)[0]
                    peers.append((ip_str, port_int))

                return peers, info_hash, peer_id

            break
        return None, None, None

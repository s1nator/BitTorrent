import bcoding
import logging
import random
import hashlib


class TorrentFileParser:
    source: str
    destination: str
    logger = logging.getLogger(__name__)

    def __init__(self, source: str, destination: str) -> None:
        self.source = source
        self.destination = destination

    def get_total_size(self, info) -> int:
        if "files" in info:
            total_size = 0
            for file in info["files"]:
                total_size += file["length"]
        else:
            return info["length"]

        return total_size

    def parse(self) -> tuple[list[str], bytes, bytes, int, dict] | None:
        try:
            self.logger.info(f"Parsing file from '{self.source}'")

            list_args_for_torrent_file = []
            with open(self.source, "rb") as torrent_file:
                raw_data = torrent_file.read()
                torrent_data = bcoding.bdecode(raw_data)

            if "announce" in torrent_data:
                if "announce-list" in torrent_data:
                    for tier in torrent_data["announce-list"]:
                        for tracker in tier:
                            list_args_for_torrent_file.append(tracker)
                elif "announce" in torrent_data:
                    list_args_for_torrent_file.append(torrent_data["announce"])

            peer_id = (
                f"-PC0001-{''.join([str(random.randint(0, 9)) for _ in range(12)])}"
            ).encode('utf-8')
            info_hash = hashlib.sha1(
                bcoding.bencode(torrent_data["info"])).digest()
            left = self.get_total_size(torrent_data["info"])

            return [
                list_args_for_torrent_file,
                info_hash,
                peer_id,
                left,
                torrent_data["info"],
            ]

        except Exception as e:
            error = f"Error: {e}"
            logging.error(error)
            raise Exception(error)

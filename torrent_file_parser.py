import bcoding, logging


class TorrentFileParser:
    source: str
    destination: str
    logger = logging.getLogger(__name__)

    def parse(self) -> list[str] | None:
        try:
            self.logger.info(f"Parsing file from '{self.source}'")

            list_args_for_torrent_file = []
            with open(self.source, "rb") as torrent_file:
                raw_data = torrent_file.read()
                torrent_data = bcoding.bdecode(raw_data)

            if "announce" in torrent_data:
                list_args_for_torrent_file.append(torrent_data["announce"])

            if "info" in torrent_data:
                info = torrent_data["info"]
                list_args_for_torrent_file.append(info["name"])

            return list_args_for_torrent_file

        except Exception as e:
            logging.error(f"Error: {e}")
            raise e

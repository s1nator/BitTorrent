from torrent_file_parser import TorrentFileParser
import requests


class LoaderTorrentFile:
    source: str
    destination: str

    def __init__(self, source, destination):
        self.source = source
        self.destination = destination

    def loader(self) -> None:
        parser = TorrentFileParser(self.source, self.destination)
        list_args = parser.parse()

        for arg in list_args[0]:
            params = {
                'info_hash': list_args[1],
                'peer_id': list_args[2],
                'uploaded': 0,
                'downloaded': 0,
                'left': list_args[3],
                'port': 6889,
                'compact': 1
            }

            request = requests.get(arg, params=params).status_code
            print(request)
            break



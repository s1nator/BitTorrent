import argparse, logging

from torrent_file_parser import TorrentFileParser
from handshake_torrent_file import HandShakeTCP


def setup_logging():
    logging.basicConfig(
        filename="bittorrent.log",
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Application started")

    parser = argparse.ArgumentParser(prog="BitTorrent")
    parser.add_argument("source", help="link to .torrent file")
    parser.add_argument("-d", "--destination", help="destination folder to save files")

    args = parser.parse_args()
    print(f"Downloading files from '{args.source}'...")

    loader = HandShakeTCP(args.source, args.destination)
    loader.handshake()


if __name__ == "__main__":
    main()

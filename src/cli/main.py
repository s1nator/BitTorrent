import argparse, logging, threading

from src.peer.handshake import HandShakeTCP


def setup_logging():
    logging.basicConfig(
        filename="bittorrent.log",
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def download_torrent(source, destination):
    loader = HandShakeTCP(source, destination)
    loader.handshake()


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Application started")

    parser = argparse.ArgumentParser(prog="BitTorrent")
    parser.add_argument("sources", nargs="+", help="paths to .torrent files")
    parser.add_argument("-d", "--destination", help="destination folder to save files")

    args = parser.parse_args()

    threads = []
    for i, source in enumerate(args.sources):
        dest = args.destination
        thread = threading.Thread(target=download_torrent, args=(source, dest))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()

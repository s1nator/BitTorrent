import argparse
import logging
import threading
import sys

from src.peer.handshake import HandShakeTCP
from src import state


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


def keyboard_listener():
    """Listen for keyboard commands: p=pause, r=resume, q=quit"""
    print("\nControls: [p]ause  [r]esume  [q]uit")
    while not state.is_stopped():
        try:
            cmd = input().strip().lower()
            if cmd == 'p':
                state.pause()
            elif cmd == 'r':
                state.resume()
            elif cmd == 'q':
                state.stop()
        except EOFError:
            break


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Application started")

    parser = argparse.ArgumentParser(prog="BitTorrent")
    parser.add_argument("sources", nargs="+", help="paths to .torrent files")
    parser.add_argument("-d", "--destination",
                        help="destination folder to save files")

    args = parser.parse_args()

    state.reset()

    kb_thread = threading.Thread(target=keyboard_listener, daemon=True)
    kb_thread.start()

    threads = []
    for i, source in enumerate(args.sources):
        dest = args.destination
        thread = threading.Thread(target=download_torrent, args=(source, dest))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    if state.is_stopped():
        print("\nDownload stopped. Progress saved - run again to resume")


if __name__ == "__main__":
    main()

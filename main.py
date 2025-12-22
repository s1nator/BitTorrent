import argparse

from parsing_torrent_file import TorrentFileParser


def main():
    parser = argparse.ArgumentParser(prog="BitTorrent")
    parser.add_argument("source", help="link to .torrent file")
    parser.add_argument("-d", "--destination", help="destination folder to save files")

    args = parser.parse_args()
    print(f"Downloading files from '{args.source}'...")

    torrent_file_parser = TorrentFileParser(args.source, args.destination)


if __name__ == "__main__":
    main()

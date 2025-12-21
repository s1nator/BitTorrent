import sys

import bcoding

from parsing_torrent_file import parsing_torrent_file



def main():
    args = sys.argv
    print("Input path to torrent file:\n")
    print(parsing_torrent_file(args[1]))


if __name__ == "__main__":
    main()
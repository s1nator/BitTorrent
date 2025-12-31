from src.progress.indicator import ProgressIndicator
import hashlib
import math
import os


class StorageManager:
    def __init__(self, torrent_info, download_dir):
        """
        Initializes the storage manager for handling file operations related to the torrent

        Args:
            torrent_info (dict): The "info" dictionary from the parsed .torrent file, containing metadata about files and pieces
            download_dir (str): The directory where torrent data will be stored
        """
        self.torrent_info = torrent_info
        self.download_dir = download_dir
        self.piece_length = torrent_info["piece length"]
        self.total_pieces = len(self.torrent_info["pieces"]) // 20
        self.pieces_status = [False] * self.total_pieces
        self.file_map = self._build_file_map()
        self.progress = ProgressIndicator(self.total_pieces)

    def get_bitfield(self) -> bytes:
        """
        Generates the bitfield bytes representing the pieces available
        """
        num_bytes = math.ceil(self.total_pieces / 8)
        bitfield = bytearray(num_bytes)

        for i, has_piece in enumerate(self.pieces_status):
            if has_piece:
                byte_index = i // 8
                bit_index = i % 8
                bitfield[byte_index] |= 1 << (7 - bit_index)

        return bytes(bitfield)

    def mark_piece_completed(self, piece_index: int):
        """
        Updates the internal status to indicate the piece is available
        """
        if 0 <= piece_index < self.total_pieces:
            self.pieces_status[piece_index] = True
            completed = sum(self.pieces_status)
            self.progress.update(completed)
            if completed == self.total_pieces:
                self.progress.close()

    def _build_file_map(self):
        """
        Builds an internal mapping between pieces and the corresponding files and offsets on disk

        Returns:
            list: A list of tuples, each containing (file_path, file_offset, size) for every file in the torrent
        """
        files = []
        if "files" in self.torrent_info:
            current_offset = 0
            for fileinfo in self.torrent_info["files"]:
                path = os.path.join(self.download_dir, *fileinfo["path"])
                length = fileinfo["length"]
                files.append(
                    {
                        "path": path,
                        "length": length,
                        "start_off": current_offset,
                        "end_off": current_offset + length,
                    }
                )
                current_offset += length
        else:
            filename = self.torrent_info["name"]
            length = self.torrent_info["length"]
            path = os.path.join(self.download_dir, filename)
            files.append(
                {"path": path, "length": length, "start_off": 0, "end_off": length}
            )

        for file in files:
            os.makedirs(os.path.dirname(file["path"]), exist_ok=True)
            if not os.path.exists(file["path"]):
                with open(file["path"], "wb") as tmp:
                    tmp.truncate(file["length"])
        return files

    def write_piece(self, piece_index: int, data: bytes):
        """
        Writes the entire piece's data into the correct location(s) on disk

        Args:
            piece_index (int): The index of the piece to write
            data (bytes): The byte content of the piece, typically piece_length long except possibly the last piece

        Raises:
            IOError: If a disk write operation fails.
        """
        global_offset = piece_index * self.piece_length
        remaining = len(data)
        data_offset = 0

        for f in self.file_map:
            if global_offset < f["end_off"]:
                file_rel_offset = max(global_offset - f["start_off"], 0)
                write_len = min(remaining, f["end_off"] - global_offset)
                with open(f["path"], "r+b") as fh:
                    fh.seek(file_rel_offset)
                    fh.write(data[data_offset : data_offset + write_len])
                remaining -= write_len
                global_offset += write_len
                data_offset += write_len
                if remaining <= 0:
                    break

    def read_piece(self, piece_index: int, offset: int, length: int) -> bytes:
        """
        Reads a segment from a piece stored on disk

        Args:
            piece_index (int): The index of the piece requested
            offset (int): The byte offset within the piece to start reading from
            length (int): The number of bytes to read from the offset

        Returns:
            bytes: The requested data segment, which may span file boundaries

        Raises:
            IOError: If a disk read operation fails.
        """
        global_offset = piece_index * self.piece_length + offset
        remaining = length
        data = bytearray()

        for f in self.file_map:
            if global_offset < f["end_off"]:
                file_rel_offset = max(global_offset - f["start_off"], 0)
                read_len = min(remaining, f["end_off"] - global_offset)
                with open(f["path"], "rb") as fh:
                    fh.seek(file_rel_offset)
                    data.extend(fh.read(read_len))
                remaining -= read_len
                global_offset += read_len
                if remaining <= 0:
                    break

        return bytes(data)

    def piece_hash_valid(self, piece_index: int, data: bytes) -> bool:
        """
        Validates the SHA1 hash of a piece against the expected hash from the .torrent

        Args:
            piece_index (int): The index of the piece being validated
            data (bytes): The piece data whose hash is to be checked

        Returns:
            bool: True if the data hash matches the expected hash
        """
        pieces_hashes = self.torrent_info["pieces"]
        piece_hash = pieces_hashes[piece_index * 20 : (piece_index + 1) * 20]
        real_hash = hashlib.sha1(data).digest()
        return real_hash == piece_hash

from src.progress.indicator import ProgressIndicator
import hashlib
import math
import os
import logging

logger = logging.getLogger(__name__)


class StorageManager:
    def __init__(self, torrent_info, download_dir):
        self.torrent_info = torrent_info
        self.download_dir = download_dir
        self.piece_length = torrent_info["piece length"]
        self.total_pieces = len(self.torrent_info["pieces"]) // 20
        self.pieces_status = [False] * self.total_pieces
        self.file_map = self._build_file_map()
        self._validate_existing_pieces()
        self.progress = ProgressIndicator(self.total_pieces)
        logger.info(
            f"StorageManager initialized for download_dir='{self.download_dir}' with {self.total_pieces} pieces"
        )

    def _validate_existing_pieces(self):
        logger.info("Validating existing data...")
        for i in range(self.total_pieces):
            try:
                # Calculate piece length (handle last piece)
                piece_len = self.piece_length
                if i == self.total_pieces - 1:
                    total_length = sum(f["length"] for f in self.file_map)
                    rem = total_length % self.piece_length
                    if rem > 0:
                        piece_len = rem

                data = self.read_piece(i, 0, piece_len)
                if self.piece_hash_valid(i, data):
                    self.pieces_status[i] = True
            except Exception:
                pass

        completed = sum(self.pieces_status)
        if completed > 0:
            logger.info(f"Found {completed} valid pieces already downloaded")

    def get_bitfield(self) -> bytes:
        num_bytes = math.ceil(self.total_pieces / 8)
        bitfield = bytearray(num_bytes)

        for i, has_piece in enumerate(self.pieces_status):
            if has_piece:
                byte_index = i // 8
                bit_index = i % 8
                bitfield[byte_index] |= 1 << (7 - bit_index)

        return bytes(bitfield)

    def mark_piece_completed(self, piece_index: int):
        if 0 <= piece_index < self.total_pieces:
            self.pieces_status[piece_index] = True
            completed = sum(self.pieces_status)
            logger.info(
                f"Piece {piece_index} marked as completed, {completed}/{self.total_pieces} pieces done"
            )
            self.progress.update(completed)
            if completed == self.total_pieces:
                logger.info("All pieces downloaded")
                self.progress.close()

    def _build_file_map(self):
        files = []
        if "files" in self.torrent_info:
            root_dir = self.torrent_info["name"]
            base_path = os.path.join(self.download_dir, root_dir)
            current_offset = 0
            for fileinfo in self.torrent_info["files"]:
                path = os.path.join(base_path, *fileinfo["path"])
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
                try:
                    with open(file["path"], "wb") as tmp:
                        tmp.truncate(file["length"])
                    logger.info(
                        f"Created file '{file['path']}' with length {file['length']} bytes"
                    )
                except Exception as e:
                    logger.error(f"Failed to create file '{file['path']}': {e}")
        return files

    def write_piece(self, piece_index: int, data: bytes):
        global_offset = piece_index * self.piece_length
        remaining = len(data)
        data_offset = 0
        try:
            for f in self.file_map:
                if global_offset < f["end_off"]:
                    file_rel_offset = max(global_offset - f["start_off"], 0)
                    write_len = min(remaining, f["end_off"] - global_offset)
                    with open(f["path"], "r+b") as fh:
                        fh.seek(file_rel_offset)
                        fh.write(data[data_offset : data_offset + write_len])
                    logger.info(
                        f"Wrote {write_len} bytes to '{f['path']}' at offset {file_rel_offset} for piece {piece_index}"
                    )
                    remaining -= write_len
                    global_offset += write_len
                    data_offset += write_len
                    if remaining <= 0:
                        break
        except Exception as e:
            logger.error(f"Error writing piece {piece_index}: {e}")

    def read_piece(self, piece_index: int, offset: int, length: int) -> bytes:
        global_offset = piece_index * self.piece_length + offset
        remaining = length
        data = bytearray()
        try:
            for f in self.file_map:
                if global_offset < f["end_off"]:
                    file_rel_offset = max(global_offset - f["start_off"], 0)
                    read_len = min(remaining, f["end_off"] - global_offset)
                    with open(f["path"], "rb") as fh:
                        fh.seek(file_rel_offset)
                        data.extend(fh.read(read_len))
                    logger.info(
                        f"Read {read_len} bytes from '{f['path']}' at offset {file_rel_offset} for piece {piece_index}"
                    )
                    remaining -= read_len
                    global_offset += read_len
                    if remaining <= 0:
                        break

        except Exception as e:
            logger.error(f"Error reading piece {piece_index}: {e}")

        return bytes(data)

    def piece_hash_valid(self, piece_index: int, data: bytes) -> bool:
        pieces_hashes = self.torrent_info["pieces"]
        piece_hash = pieces_hashes[piece_index * 20 : (piece_index + 1) * 20]
        real_hash = hashlib.sha1(data).digest()
        valid = real_hash == piece_hash
        if not valid:
            logger.warning(
                f"Piece {piece_index} hash mismatch: expected {piece_hash.hex()}, got {real_hash.hex()}"
            )

        return valid

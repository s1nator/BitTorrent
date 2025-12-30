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
        self.file_map = self._build_file_map()

    def _build_file_map(self):
        """
        Builds an internal mapping between pieces and the corresponding files and offsets on disk

        Returns:
            list: A list of tuples, each containing (file_path, file_offset, size) for every file in the torrent
        """
        raise NotImplementedError()

    def write_piece(self, piece_index: int, data: bytes):
        """
        Writes the entire piece's data into the correct location(s) on disk

        Args:
            piece_index (int): The index of the piece to write
            data (bytes): The byte content of the piece, typically piece_length long except possibly the last piece

        Raises:
            IOError: If a disk write operation fails.
        """
        raise NotImplementedError()

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
        raise NotImplementedError()

    def piece_hash_valid(self, piece_index: int, data: bytes) -> bool:
        """
        Validates the SHA1 hash of a piece against the expected hash from the .torrent

        Args:
            piece_index (int): The index of the piece being validated
            data (bytes): The piece data whose hash is to be checked

        Returns:
            bool: True if the data hash matches the expected hash
        """
        raise NotImplementedError()

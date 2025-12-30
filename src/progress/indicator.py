import sys


class ProgressIndicator:
    def __init__(self, total_pieces: int, bar_length: int = 50):
        """
        Initializes the progress indicator.

        Args:
            total_pieces (int): The total number of pieces to download.
            bar_length (int): The length of the progress bar in characters.
        """
        self.total_pieces = total_pieces
        self.bar_length = bar_length

    def update(self, completed_pieces: int):
        """
        Updates the progress bar based on the number of completed pieces.

        Args:
            completed_pieces (int): The number of pieces downloaded so far.
        """
        if self.total_pieces == 0:
            return

        progress = completed_pieces / self.total_pieces
        block = int(round(self.bar_length * progress))

        bar = "#" * block + "-" * (self.bar_length - block)
        text = f"\rProgress: [{bar}] {progress * 100:.2f}%"

        sys.stdout.write(text)
        sys.stdout.flush()

    def close(self):
        sys.stdout.write("\n")
        sys.stdout.flush()

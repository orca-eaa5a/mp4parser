class Mp4Modifier(object):
    def __init__(self, chunks) -> None:
        """
        Args:
            chunks (list): mp4 parser chunks list
        """
        self.chunks = chunks
        pass

    def replace_track_stbl(self, trak_box):
        pass


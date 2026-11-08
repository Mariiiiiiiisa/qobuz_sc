class TrackDownloadError(Exception):
    def __init__(self, track_id, original=None):
        self.track_id = track_id
        self.original = original
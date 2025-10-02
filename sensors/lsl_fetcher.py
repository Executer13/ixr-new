# lsl_fetcher.py

from pylsl import resolve_streams, StreamInfo

class LSLFetcher:
    """
    Simple LSL fetcher to scan for available streams.
    """
    def __init__(self):
        pass

    def get_available_streams(self):
        print("get_available_streams")
        # Returns a list of StreamInfo objects
        streams = resolve_streams()
        return streams

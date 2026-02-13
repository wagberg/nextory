import base64
import secrets
import uuid
from dataclasses import dataclass


@dataclass
class DeviceId:
    """Device ID container."""
    value: str

    @classmethod
    def from_bytes(cls, random_bytes: bytes) -> "DeviceId":
        """Create device ID from bytes."""
        return cls(encode_device_id(random_bytes))
    
    @classmethod
    def from_string(cls, value: str) -> "DeviceId":
        """Create device ID from string."""
        return cls.from_bytes(uuid.uuid3(uuid.NAMESPACE_DNS, value).bytes)

    @property
    def bytes(self) -> bytes:
        """Return device ID as bytes."""
        return decode_device_id(self.value)
    
def encode_device_id(random_bytes: bytes) -> str:
    """Encode bytes to Firebase Installation ID (FID)."""
    return base64.urlsafe_b64encode(random_bytes).decode("ascii").rstrip("=")

def decode_device_id(device_id: str) -> bytes:
    """Decode a device id to bytes."""
    # Add padding if necessary
    if len(device_id) % 4 != 0:
        device_id += "=" * (4 - len(device_id) % 4)
    return base64.urlsafe_b64decode(device_id)


def generate_device_id() -> str:
    """Generate device id for header X-Device-Id

    These are 22-character base64url encoded strings.
    """
    return secrets.token_urlsafe(16)

@dataclass
class PlaylistItem:
    path: str
    length: str | None
    title: str | None
    stream_info: dict[str, str] | None
    key: str | None

def parse_m3u(m3u_data: str) -> list[PlaylistItem]:
    """Lightweight M3U/M3U8 parser for playlist URL extraction.

    This parser returns a flat list of playlist items with basic metadata.
    Supports HLS master playlist tags (#EXT-X-STREAM-INF, #EXT-X-KEY) for
    stream selection and quality sorting, but does not preserve segment-level
    details or playlist structure.

    Based on https://github.com/dvndrsn/M3uParser/blob/master/m3uparser.py
    """
    # From Mozilla gecko source: https://github.com/mozilla/gecko-dev/blob/c4c1adbae87bf2d128c39832d72498550ee1b4b8/dom/media/DecoderTraits.cpp#L47-L52

    m3u_lines = m3u_data.splitlines()

    playlist: list[PlaylistItem] = []

    length = None
    title = None
    stream_info: dict[str, str] | None = None
    key = None

    for line in m3u_lines:
        line = line.strip()  # noqa: PLW2901
        if line.startswith("#EXTINF:"):
            # Get length and title from #EXTINF line
            info = line.split("#EXTINF:")[1].split(",", 1)
            if len(info) != 2:
                continue
            length = info[0].strip()[0]
            if length == "-1":
                length = None
            title = info[1].strip()
        elif line.startswith("#EXT-X-STREAM-INF:"):
            # HLS master playlist variant stream properties (BANDWIDTH, RESOLUTION, etc.)
            # https://datatracker.ietf.org/doc/html/draft-pantos-http-live-streaming-19#section-10
            stream_info = {}
            for part in line.replace("#EXT-X-STREAM-INF:", "").split(","):
                if "=" not in part:
                    continue
                kev_value_parts = part.strip().split("=")
                stream_info[kev_value_parts[0]] = kev_value_parts[1]
        elif line.startswith("#EXT-X-KEY:"):
            # Extract encryption key URI from master/media playlist
            # METHOD=NONE means no encryption, so explicitly clear the key
            if "METHOD=NONE" in line:
                key = None
            elif ",URI=" in line:
                key = line.split(",URI=")[1].strip('"')
        elif line.startswith("#"):
            # Ignore other extensions
            continue
        elif len(line) != 0:
            filepath = line
            if "%20" in filepath:
                # apparently VLC manages to encode spaces in filenames
                filepath = filepath.replace("%20", " ")
            # replace Windows directory separators
            filepath = filepath.replace("\\", "/")
            playlist.append(
                PlaylistItem(
                    path=filepath, length=length, title=title, stream_info=stream_info, key=key
                )
            )
            # reset the song variables so it doesn't use the same EXTINF more than once
            length = None
            title = None
            stream_info = None

    return playlist


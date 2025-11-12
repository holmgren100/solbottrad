# imghdr.py - shim for Python 3.13 (stdlib imghdr was removed)
import mimetypes

def what(file, h=None):
    # Minimal implementation used by tweepy for media type detection.
    # Returns something like "png", "jpeg", "gif", or None.
    filename = None
    try:
        if isinstance(file, (str, bytes)):
            filename = file.decode("utf-8", "ignore") if isinstance(file, bytes) else file
        else:
            filename = getattr(file, "name", None)
    except Exception:
        filename = None

    if filename:
        typ, _ = mimetypes.guess_type(filename)
        if typ and "/" in typ:
            return typ.split("/")[-1]
    return None
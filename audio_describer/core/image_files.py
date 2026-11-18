"""Which files are photos or stickers, and which frames to send to the model."""
import io
import os

IMAGE_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif",
})
VIDEO_EXTENSIONS = frozenset({
    ".mp4", ".avi", ".mkv", ".webm", ".mov", ".flv", ".wmv", ".mpeg", ".mpg",
    ".3gp", ".ogv", ".ts", ".m4v", ".divx",
})
# Telegram animated stickers are a custom lottie zip. Not described.
SKIPPED_EXTENSIONS = frozenset({".tgs"})

IMAGE_WILDCARD = "*.jpg;*.jpeg;*.png;*.webp;*.gif;*.bmp;*.tif;*.tiff;*.heic;*.heif"


def image_dialog_wildcard():
    from ..i18n_setup import _
    return _("Photos and stickers") + "|" + IMAGE_WILDCARD


def media_dialog_wildcard():
    from ..i18n_setup import _
    from .. import config
    videos = config.SUPPORTED_VIDEO_FORMATS
    return (
        _("Video and images") + "|" + videos + ";" + IMAGE_WILDCARD + "|"
        + _("Video files") + "|" + videos + "|"
        + _("Photos and stickers") + "|" + IMAGE_WILDCARD
    )


def extension_of(path):
    return os.path.splitext(path or "")[1].lower()


def is_image_path(path):
    return extension_of(path) in IMAGE_EXTENSIONS


def is_video_path(path):
    return extension_of(path) in VIDEO_EXTENSIONS


def frame_sample_indices(frame_count, maximum=6):
    """Indexes spread across an animation. One frame stays one frame."""
    count = int(frame_count or 0)
    if count <= 0:
        return []
    if count == 1:
        return [0]
    limit = max(2, int(maximum))
    if count <= limit:
        return list(range(count))
    last = count - 1
    return [int(round(i * last / (limit - 1))) for i in range(limit)]


def _register_heif():
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except Exception:
        return


def load_image_frames(path, maximum=6):
    """JPEG bytes for one still, or several frames of an animated gif or webp."""
    _register_heif()
    from PIL import Image

    frames = []
    with Image.open(path) as image:
        count = int(getattr(image, "n_frames", 1) or 1)
        for index in frame_sample_indices(count, maximum if count > 1 else 1):
            image.seek(index)
            buffer = io.BytesIO()
            image.convert("RGB").save(buffer, format="JPEG", quality=80)
            frames.append({
                "index": index,
                "count": count,
                "jpeg": buffer.getvalue(),
            })
    if not frames:
        raise ValueError("No frame could be read.")
    return frames

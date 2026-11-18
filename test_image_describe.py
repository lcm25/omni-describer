"""Image types, animation frames, and the description prompt. No network."""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audio_describer.core.image_describe import gemini_image_parts, image_request
from audio_describer.core.image_files import (
    frame_sample_indices,
    is_image_path,
    is_video_path,
    load_image_frames,
)
from audio_describer.core.image_prompt import image_prompt


def test_types():
    assert is_image_path("foto.JPG")
    assert is_image_path("sticker.webp")
    assert is_image_path("anim.gif")
    assert is_image_path("shot.png")
    assert is_image_path("scan.tiff")
    assert is_image_path("phone.heic")
    assert not is_image_path("sticker.tgs")
    assert not is_image_path("clip.mp4")
    assert is_video_path("clip.MP4")
    assert not is_video_path("foto.jpg")


def test_sample_indexes():
    assert frame_sample_indices(1) == [0]
    assert frame_sample_indices(0) == []
    assert frame_sample_indices(4, 6) == [0, 1, 2, 3]
    picked = frame_sample_indices(12, 6)
    assert picked[0] == 0 and picked[-1] == 11 and len(picked) == 6
    assert picked == sorted(set(picked))


def _gif_bytes(colors):
    from PIL import Image
    frames = [Image.new("RGB", (8, 8), color) for color in colors]
    buffer = io.BytesIO()
    frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:], duration=80, loop=0)
    return buffer.getvalue()


def test_gif_frames(tmp_path=None):
    from PIL import Image
    path = Path(__file__).resolve().parent / "_tmp_anim.gif"
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 0, 0), (255, 255, 255), (10, 10, 10), (20, 20, 20)]
    path.write_bytes(_gif_bytes(colors))
    try:
        frames = load_image_frames(path, maximum=6)
        assert len(frames) == 6
        assert frames[0]["jpeg"][:2] == b"\xff\xd8"
        assert frames[0]["jpeg"] != frames[-1]["jpeg"]
        assert frames[-1]["count"] == 8
    finally:
        path.unlink(missing_ok=True)


def test_webp_frames():
    from PIL import Image
    path = Path(__file__).resolve().parent / "_tmp_anim.webp"
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    frames = [Image.new("RGB", (8, 8), color) for color in colors]
    try:
        frames[0].save(path, format="WEBP", save_all=True, append_images=frames[1:], duration=80, loop=0)
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise AssertionError(f"Pillow could not write an animated webp: {exc}") from exc
    try:
        loaded = load_image_frames(path, maximum=6)
        assert len(loaded) == 4
        assert loaded[0]["jpeg"] != loaded[-1]["jpeg"]
    finally:
        path.unlink(missing_ok=True)


def test_prompt_covers_the_brief():
    short = image_prompt("short", animated=False)
    assert "um parágrafo curto" in short
    for phrase in (
        "foto, figurinha, meme, captura de tela ou desenho",
        "assunto principal",
        "expressões e as ações",
        "texto visível exatamente",
        "cores só quando",
        "emoção ou a piada",
    ):
        assert phrase in short, phrase
    assert "movimento" not in short
    moving = image_prompt("short", animated=True)
    assert "descreva o movimento" in moving
    long = image_prompt("long", animated=True)
    assert "mais detalhes" in long and "movimento" in long
    follow = image_prompt("short", question="Que texto aparece?")
    assert "Que texto aparece?" in follow
    assert "Responda só a esta pergunta" in follow


def test_request_includes_frames_as_text():
    frames = [
        {"index": 0, "count": 2, "jpeg": b"\xff\xd8jpeg-a"},
        {"index": 1, "count": 2, "jpeg": b"\xff\xd8jpeg-b"},
    ]
    parts = gemini_image_parts("descreva", frames)
    assert parts[0] == {"text": "Quadro 1 de 2."}
    assert parts[1]["inline_data"]["byte_length"] == len(frames[0]["jpeg"])
    assert parts[-1] == {"text": "descreva"}
    prepared = image_request("openai", "gpt-4o", "key", "descreva", frames)
    body = prepared["body"]
    assert "response_format" not in body
    content = body["messages"][1]["content"]
    assert any(part.get("type") == "image_url" for part in content)
    assert any(part.get("text") == "descreva" for part in content)


if __name__ == "__main__":
    test_types()
    test_sample_indexes()
    test_gif_frames()
    test_webp_frames()
    test_prompt_covers_the_brief()
    test_request_includes_frames_as_text()
    print("image describe checks passed")

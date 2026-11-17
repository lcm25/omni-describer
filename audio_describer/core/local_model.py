"""On-demand llama.cpp vision models. Nothing here is shipped in the installer."""
import os
import re
import subprocess
import tempfile

from ..models import config_model

RUNTIME = {
    "id": "llama-vulkan-b12477",
    "url": "https://github.com/ggml-org/llama.cpp/releases/download/b12477/llama-b12477-bin-win-vulkan-x64.zip",
    "sha256": "846c47a25198dea5721056867cd047013a2d84b60ab844daa65f74076ac4e22f",
    "size": 38304567,
    "exe_names": ("llama-mtmd-cli.exe", "llama-cli.exe"),
}

LOCAL_MODELS = (
    {
        "id": "qwen25vl-3b",
        "label": "Qwen2.5-VL 3B, about 3 GB, 8 GB of RAM",
        "files": (
            {
                "name": "Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf",
                "role": "model",
                "url": "https://huggingface.co/ggml-org/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf",
                "sha256": "d02fe9b69ad8cadbbd228e387667af66612c44bed29ffc8eb1e7caf9ac486c12",
                "size": 1929901056,
            },
            {
                "name": "mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf",
                "role": "mmproj",
                "url": "https://huggingface.co/ggml-org/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf",
                "sha256": "980c9b2f78c04e6cff93d277ada09e768394f112d75db3b4e9dea8a69f9fb904",
                "size": 844757728,
            },
        ),
    },
    {
        "id": "qwen25vl-7b",
        "label": "Qwen2.5-VL 7B, about 6 GB, 16 GB of RAM",
        "files": (
            {
                "name": "Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf",
                "role": "model",
                "url": "https://huggingface.co/ggml-org/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf",
                "sha256": "9258bf05b12686d097ff3b6b18d968ab393649780aa2b3cd67fec43d50554392",
                "size": 4683072032,
            },
            {
                "name": "mmproj-Qwen2.5-VL-7B-Instruct-Q8_0.gguf",
                "role": "mmproj",
                "url": "https://huggingface.co/ggml-org/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/mmproj-Qwen2.5-VL-7B-Instruct-Q8_0.gguf",
                "sha256": "2ddb555391bae966e412deab9e07b58afa18bcc06930ba0f1c78a3695ab9e506",
                "size": 853119712,
            },
        ),
    },
)


def model_by_id(model_id):
    for item in LOCAL_MODELS:
        if item["id"] == model_id:
            return item
    return LOCAL_MODELS[0]


def models_dir():
    if config_model.APP_DATA_DIR and os.path.basename(config_model.APP_DATA_DIR) == "Dados":
        return os.path.join(config_model.APP_DATA_DIR, "modelos")
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Descritudo", "modelos")


def runtime_dir():
    return os.path.join(models_dir(), "llama")


def model_file(model, role):
    spec = next(item for item in model["files"] if item["role"] == role)
    return os.path.join(models_dir(), model["id"], spec["name"]), spec


def is_installed(model_id):
    model = model_by_id(model_id)
    for role in ("model", "mmproj"):
        path, spec = model_file(model, role)
        if not os.path.isfile(path) or os.path.getsize(path) != spec["size"]:
            return False
    return find_runtime_exe() is not None


def find_runtime_exe():
    folder = runtime_dir()
    if not os.path.isdir(folder):
        return None
    for root, _dirs, files in os.walk(folder):
        for name in RUNTIME["exe_names"]:
            if name in files:
                return os.path.join(root, name)
    return None


def bytes_still_needed(model_id):
    model = model_by_id(model_id)
    needed = 0
    if find_runtime_exe() is None and not os.path.isfile(os.path.join(runtime_dir(), "runtime.zip")):
        partial = os.path.join(runtime_dir(), "runtime.zip.part")
        have = os.path.getsize(partial) if os.path.isfile(partial) else 0
        needed += max(0, RUNTIME["size"] - have)
    for spec in model["files"]:
        path = os.path.join(models_dir(), model["id"], spec["name"])
        if os.path.isfile(path) and os.path.getsize(path) == spec["size"]:
            continue
        partial = path + ".part"
        have = os.path.getsize(partial) if os.path.isfile(partial) else 0
        needed += max(0, spec["size"] - have)
    return needed


def remove_model(model_id):
    folder = os.path.join(models_dir(), model_by_id(model_id)["id"])
    if os.path.isdir(folder):
        import shutil
        shutil.rmtree(folder, ignore_errors=True)


def mtmd_command(exe, model_path, mmproj_path, image_paths, prompt):
    command = [exe, "-m", model_path, "--mmproj", mmproj_path, "-p", prompt, "-n", "500", "-ngl", "99"]
    for path in image_paths or []:
        command.extend(["--image", path])
    return command


def parse_timed_lines(text, duration=0):
    """Lines like '01:20 | texto' become (start, end, text). Otherwise one block."""
    rows = []
    for line in (text or "").splitlines():
        match = re.match(r"\s*(\d{1,2}):(\d{2})\s*\|\s*(.+)", line.strip())
        if not match:
            continue
        seconds = int(match.group(1)) * 60 + int(match.group(2))
        rows.append((seconds, match.group(3).strip()))
    if not rows:
        body = (text or "").strip()
        if not body:
            return []
        return [(0.0, float(duration or 1), body)]
    parsed = []
    for index, (seconds, line) in enumerate(rows):
        end = rows[index + 1][0] if index + 1 < len(rows) else max(float(duration or 0), seconds + 1)
        if end <= seconds:
            end = seconds + 1
        parsed.append((float(seconds), float(end), line))
    return parsed


def local_video_prompt():
    return (
        "Descreva o vídeo em português do Brasil, em linhas curtas. "
        "Você vê só alguns quadros parados, não o filme inteiro, e não há transcrição do áudio. "
        "Para cada momento, uma linha no formato MM:SS | texto. "
        "Diga o que acontece, as ações das pessoas e qualquer texto visível, exatamente como aparece."
    )


def describe_local(frames, prompt):
    """Run the local vision tool. Does not open a network connection."""
    from .image_describe import ImageDescribeError
    model_id = config_model.get_setting("analysis_model") or LOCAL_MODELS[0]["id"]
    if model_id not in {item["id"] for item in LOCAL_MODELS}:
        model_id = LOCAL_MODELS[0]["id"]
    if not is_installed(model_id):
        raise ImageDescribeError("missing")
    model = model_by_id(model_id)
    model_path, _spec = model_file(model, "model")
    mmproj_path, _mm = model_file(model, "mmproj")
    exe = find_runtime_exe()
    images = []
    temps = []
    try:
        for frame in frames or []:
            handle = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            handle.write(frame["jpeg"])
            handle.close()
            temps.append(handle.name)
            images.append(handle.name)
        command = mtmd_command(exe, model_path, mmproj_path, images, prompt)
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()[-400:]
            raise ImageDescribeError(detail or "local-failed")
        text = (result.stdout or "").strip()
        if not text:
            raise ImageDescribeError("empty")
        return text
    finally:
        for path in temps:
            if os.path.exists(path):
                os.remove(path)

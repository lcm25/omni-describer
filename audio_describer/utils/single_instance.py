"""One process. A second launch sends its files to the first and exits."""
import json
import os
import socket
import threading

from ..models import config_model


def port_path(folder=None):
    base = folder or config_model.APP_DATA_DIR
    return os.path.join(base, "instance.port")


def forward(paths, folder=None, timeout=1.0):
    path = port_path(folder)
    try:
        port = int(open(path, encoding="ascii").read().strip())
        payload = json.dumps(list(paths or [])).encode("utf-8") + b"\n"
        with socket.create_connection(("127.0.0.1", port), timeout=timeout) as sock:
            sock.sendall(payload)
            ack = sock.recv(16)
        return ack.startswith(b"ok")
    except (OSError, ValueError):
        return False


def listen(handler, folder=None):
    """Start a daemon thread. handler(paths) runs on that thread."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(8)
    port = server.getsockname()[1]
    path = port_path(folder)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="ascii") as handle:
        handle.write(str(port))

    def loop():
        while True:
            try:
                conn, _addr = server.accept()
            except OSError:
                return
            with conn:
                data = b""
                while b"\n" not in data and len(data) < 1024 * 1024:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                try:
                    paths = json.loads(data.decode("utf-8").strip() or "[]")
                except json.JSONDecodeError:
                    paths = []
                try:
                    handler(list(paths))
                except Exception:
                    pass
                try:
                    conn.sendall(b"ok")
                except OSError:
                    pass

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return server

# tools/rclone_io.py
import json, os, subprocess, time
from pathlib import Path
from typing import List
from dotenv import load_dotenv   
load_dotenv()                       

REMOTE = os.getenv("ONEDRIVE_REMOTE", "onedrv:")
ROOT = os.getenv("ROOT_PATH", "")

CACHE = Path("data/cache/folders.json")
CACHE_TTL = 600  # seconds

def _run(cmd: list[str]) -> str:
    """
    Run an rclone command and return stdout text.
    """
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n{res.stderr.decode(errors='ignore')}"
        )
    return res.stdout.decode(errors="ignore")

def list_folders(use_cache: bool = True) -> List[str]:
    """
    List all OneDrive folders.
    """
    if use_cache and CACHE.exists() and (time.time() - CACHE.stat().st_mtime) < CACHE_TTL:
        data = json.loads(CACHE.read_text())
    else:
        cmd = ["rclone", "lsjson", f"{REMOTE}{ROOT}", "--dirs-only", "--recursive"]
        out = _run(cmd)
        data = json.loads(out) if out.strip() else []
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(data))

    paths = []
    for obj in data:
        rel = obj.get("Path") or obj.get("Name")
        if rel:
            paths.append(rel)
    return sorted(set(paths))

def ensure_path(rel_path: str):
    """
    Create a folder path if it doesn’t exist.
    """
    _run(["rclone", "mkdir", f"{REMOTE}{ROOT}{rel_path}"])

def move_local_to_remote(local_path: str, dest_rel_path: str, dest_filename: str):
    """
    Move a local file into OneDrive at the chosen folder + filename.
    """
    dst = f"{REMOTE}{ROOT}{dest_rel_path}/{dest_filename}"
    _run(["rclone", "moveto", local_path, dst])
    return dst

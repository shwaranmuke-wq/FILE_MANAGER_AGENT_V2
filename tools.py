"""
tools.py — file-system operations exposed to the AI agent.

Each function returns a plain dict (JSON-serializable) so it can be fed
straight back to the model as a tool result.
"""

from pathlib import Path
import subprocess
import shutil
import platform
import time

# Password required to edit the content of an existing file.
# Change this whenever you like — it's only checked here.
EDIT_PASSWORD = "123"

# pyautogui expects "win" written as "winleft"
SHORTCUT_ALIASES = {
    "win": "winleft",
    "windows": "winleft",
    "cmd": "command",   # macOS
}


def list_files(directory: str):
    """List files and folders inside a directory (max 100 entries)."""
    path = Path(directory)

    if not path.exists():
        return {"error": f"Directory does not exist: {directory}"}

    if not path.is_dir():
        return {"error": f"Not a directory: {directory}"}

    items = []
    for item in path.iterdir():
        items.append({
            "name": item.name,
            "type": "folder" if item.is_dir() else "file"
        })
        if len(items) > 100:
            break

    return {
        "directory": str(path),
        "items": items
    }


def create_file(directory: str, filename: str):
    """Create a new, empty file."""
    path = Path(directory) / filename

    if path.exists():
        return {"error": f"File already exists: {path}"}

    path.touch()
    return {"success": True, "created": str(path)}


def remove_file(directory: str, filename: str):
    """Delete a file."""
    path = Path(directory) / filename

    if not path.exists():
        return {"error": f"File does not exist: {path}"}
    if not path.is_file():
        return {"error": f"Not a file: {path}"}

    path.unlink()
    return {"success": True, "removed": str(path)}


def open_file(directory: str, filename: str):
    """Open a file with the OS default handler (cross-platform)."""
    path = Path(directory) / filename

    if not path.exists():
        return {"error": f"File does not exist: {path}"}
    if not path.is_file():
        return {"error": f"Not a file: {path}"}

    system = platform.system()
    try:
        if system == "Windows":
            subprocess.Popen(["notepad.exe", str(path)])
        elif system == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as e:
        return {"error": str(e)}

    return {"success": True, "opened": str(path)}


def write_file(directory: str, filename: str, content: str):
    """Write (overwrite) text content into a file."""
    path = Path(directory) / filename

    try:
        path.write_text(content, encoding="utf-8")
        return {"success": True, "written": str(path)}
    except Exception as e:
        return {"error": str(e)}


def read_file(directory: str, filename: str):
    """Read text content from a file (useful for the model to inspect files)."""
    path = Path(directory) / filename

    if not path.exists():
        return {"error": f"File does not exist: {path}"}
    if not path.is_file():
        return {"error": f"Not a file: {path}"}

    try:
        content = path.read_text(encoding="utf-8")
        return {"success": True, "content": content}
    except Exception as e:
        return {"error": str(e)}


def copy_file(source_directory: str, filename: str, destination_directory: str):
    """Copy a file to another directory."""
    source = Path(source_directory) / filename
    destination = Path(destination_directory) / filename

    if not source.exists():
        return {"error": f"File does not exist: {source}"}
    if not source.is_file():
        return {"error": f"Not a file: {source}"}
    if not Path(destination_directory).is_dir():
        return {"error": f"Destination directory does not exist: {destination_directory}"}
    if destination.exists():
        return {"error": f"Destination file already exists: {destination}"}

    shutil.copy2(source, destination)
    return {"success": True, "source": str(source), "destination": str(destination)}


def move_file(source_directory: str, filename: str, destination_directory: str):
    """Move a file to another directory."""
    source = Path(source_directory) / filename
    destination = Path(destination_directory) / filename

    if not source.exists():
        return {"error": f"File does not exist: {source}"}
    if not source.is_file():
        return {"error": f"Not a file: {source}"}
    if not Path(destination_directory).is_dir():
        return {"error": f"Destination directory does not exist: {destination_directory}"}
    if destination.exists():
        return {"error": f"Destination file already exists: {destination}"}

    shutil.move(str(source), str(destination))
    return {"success": True, "source": str(source), "destination": str(destination)}


def rename_file(directory: str, old_name: str, new_name: str):
    """Rename a file within the same directory."""
    old_path = Path(directory) / old_name
    new_path = Path(directory) / new_name

    if not old_path.exists():
        return {"error": f"File does not exist: {old_path}"}
    if not old_path.is_file():
        return {"error": f"Not a file: {old_path}"}
    if new_path.exists():
        return {"error": f"A file with that name already exists: {new_path}"}

    old_path.rename(new_path)
    return {"success": True, "old_name": old_name, "new_name": new_name}


def edit_file(directory: str, filename: str, content: str, password: str):
    """Edit (overwrite) the FULL content of an EXISTING file. Requires a password.

    Prefer str_replace_in_file for small/targeted changes — rewriting an
    entire file as one string is slow and risks the model's output being
    cut off mid-file on larger files, which corrupts the write.
    """
    if password != EDIT_PASSWORD:
        return {"error": "Incorrect password. Edit denied."}

    path = Path(directory) / filename

    if not path.exists():
        return {"error": f"File does not exist: {path}. Use create_file or write_file to make a new one."}
    if not path.is_file():
        return {"error": f"Not a file: {path}"}

    try:
        path.write_text(content, encoding="utf-8")
        return {"success": True, "edited": str(path)}
    except Exception as e:
        return {"error": str(e)}


def str_replace_in_file(directory: str, filename: str, old_str: str, new_str: str, password: str):
    """Replace one exact, unique piece of text inside an EXISTING file. Requires a password.

    old_str must appear in the file exactly once — include enough
    surrounding context to make it unique. This is the preferred way to
    edit existing files: only the changed snippet needs to be sent, not
    the whole file, so it's fast, cheap, and can't get truncated mid-file.
    """
    if password != EDIT_PASSWORD:
        return {"error": "Incorrect password. Edit denied."}

    path = Path(directory) / filename

    if not path.exists():
        return {"error": f"File does not exist: {path}"}
    if not path.is_file():
        return {"error": f"Not a file: {path}"}

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": str(e)}

    count = content.count(old_str)
    if count == 0:
        return {"error": "old_str was not found in the file — no changes made."}
    if count > 1:
        return {"error": f"old_str matches {count} places in the file. It must be unique — add more surrounding context and try again."}

    new_content = content.replace(old_str, new_str, 1)

    try:
        path.write_text(new_content, encoding="utf-8")
        return {"success": True, "edited": str(path)}
    except Exception as e:
        return {"error": str(e)}


def press_shortcut(combo: str, delay: float = 0.0):
    """Press a keyboard shortcut, e.g. 'ctrl+c', 'alt+tab', 'win+d'."""
    keys = [SHORTCUT_ALIASES.get(k.strip().lower(), k.strip().lower()) for k in combo.split("+")]

    if delay:
        time.sleep(delay)

    try:
        import pyautogui  # imported lazily: it is slow to load
        pyautogui.hotkey(*keys)
        return {"success": True, "pressed": "+".join(keys)}
    except Exception as e:
        return {"error": str(e)}


def create_folder(directory: str, folder_name: str):
    """Create a new folder."""
    path = Path(directory) / folder_name

    if path.exists():
        return {"error": f"Already exists: {path}"}

    path.mkdir()
    return {"success": True, "created": str(path)}

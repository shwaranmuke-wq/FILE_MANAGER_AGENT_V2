"""
tool_schemas.py — OpenAI/Ollama-style function-calling schemas for each
function in tools.py. Ollama's chat API accepts this `tools` format for
models that support tool calling (qwen3 does).
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and folders inside a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Path to the directory to list."}
                },
                "required": ["directory"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new, empty file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "filename": {"type": "string"},
                },
                "required": ["directory", "filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_file",
            "description": "Delete a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "filename": {"type": "string"},
                },
                "required": ["directory", "filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_file",
            "description": "Open a file with the operating system's default application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "filename": {"type": "string"},
                },
                "required": ["directory", "filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write (overwrite) text content into a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "filename": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["directory", "filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the text content of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "filename": {"type": "string"},
                },
                "required": ["directory", "filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "copy_file",
            "description": "Copy a file from one directory to another.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_directory": {"type": "string"},
                    "filename": {"type": "string"},
                    "destination_directory": {"type": "string"},
                },
                "required": ["source_directory", "filename", "destination_directory"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Move a file from one directory to another.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_directory": {"type": "string"},
                    "filename": {"type": "string"},
                    "destination_directory": {"type": "string"},
                },
                "required": ["source_directory", "filename", "destination_directory"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rename_file",
            "description": "Rename a file within the same directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "old_name": {"type": "string"},
                    "new_name": {"type": "string"},
                },
                "required": ["directory", "old_name", "new_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "str_replace_in_file",
            "description": "Preferred way to edit an existing file: replace one exact, unique snippet of text with another, without resending the whole file. old_str must match the file's content exactly, including whitespace, and appear only once — include enough surrounding lines to make it unique. The user will be asked to enter a password locally to approve this — you do not need to know or provide it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "filename": {"type": "string"},
                    "old_str": {"type": "string", "description": "Exact text to find, must be unique in the file."},
                    "new_str": {"type": "string", "description": "Text to replace it with."},
                },
                "required": ["directory", "filename", "old_str", "new_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Overwrite the ENTIRE text content of a file that already exists. Only use this for short files or a full rewrite — for a small/targeted change to a larger file, use str_replace_in_file instead so you don't have to resend the whole file. The user will be asked to enter a password locally to approve this — you do not need to know or provide it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "filename": {"type": "string"},
                    "content": {"type": "string", "description": "The new full content of the file."},
                },
                "required": ["directory", "filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_shortcut",
            "description": "Press a keyboard shortcut / hotkey combo, e.g. 'ctrl+c', 'alt+tab', 'win+d'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "combo": {"type": "string", "description": "Keys joined with '+', e.g. 'ctrl+shift+esc'."},
                    "delay": {"type": "number", "description": "Optional seconds to wait before pressing."},
                },
                "required": ["combo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Create a new folder inside a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "folder_name": {"type": "string"},
                },
                "required": ["directory", "folder_name"],
            },
        },
    },
]

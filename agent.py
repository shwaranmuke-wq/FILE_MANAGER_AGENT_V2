"""
agent.py — a terminal-based file-management AI agent.

Talks to the Groq API (free tier) running openai/gpt-oss-20b, gives it
the file-system tools defined in tools.py, and lets it plan + execute
multi-step file operations from plain-English requests.

Requires a free Groq API key: https://console.groq.com/keys
Set it as an environment variable before running:
    export GROQ_API_KEY="your-key-here"      # macOS/Linux
    setx GROQ_API_KEY "your-key-here"         # Windows (new shells)

Run:
    python agent.py
"""

import json
import os
import getpass

from groq import Groq

import tools
from tool_schemas import TOOLS

MODEL = "openai/gpt-oss-20b"

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise SystemExit(
        "GROQ_API_KEY is not set. Get a free key at "
        "https://console.groq.com/keys and set it as an environment "
        "variable before running this script."
    )

client = Groq(api_key=api_key)

# Maps tool name (as the model will call it) -> actual Python function
FUNCTION_MAP = {
    "list_files": tools.list_files,
    "create_file": tools.create_file,
    "remove_file": tools.remove_file,
    "open_file": tools.open_file,
    "write_file": tools.write_file,
    "read_file": tools.read_file,
    "copy_file": tools.copy_file,
    "move_file": tools.move_file,
    "rename_file": tools.rename_file,
    "create_folder": tools.create_folder,
    "edit_file": tools.edit_file,
    "str_replace_in_file": tools.str_replace_in_file,
    "press_shortcut": tools.press_shortcut,
}

# Actions the agent should confirm with the user before running
DESTRUCTIVE_TOOLS = {"remove_file", "move_file", "rename_file", "write_file", "press_shortcut"}

# Actions that require a password, entered locally (never sent to the model)
PASSWORD_PROTECTED_TOOLS = {"edit_file", "str_replace_in_file"}

SYSTEM_PROMPT = """You are a local file-management assistant running on the \
user's own machine. You can list, create, read, write, rename, move, copy \
and delete files, create folders, edit existing file content, and press \
keyboard shortcuts, using the tools available to you.

Rules:
- Always confirm the directory/path you are about to act on if it is ambiguous.
- Use list_files first when you are unsure what exists in a directory.
- Use write_file only to create a new file or set its initial content. To \
change the content of a file that already EXISTS, prefer str_replace_in_file \
for a small/targeted change (it only needs the exact snippet being changed, \
not the whole file — safer and faster). Only use edit_file for short files \
or when the whole file genuinely needs to be rewritten. Either way, the \
user will be prompted locally for a password to approve it — you do not \
need to ask them for it yourself.
- Only call one tool at a time, then look at the result before deciding the \
next step.
- Once the user's request is fully done, reply in plain text summarizing \
what you did. Do not call any more tools after that.
"""


def confirm(tool_name: str, args: dict) -> bool:
    print(f"\n⚠️  The model wants to run: {tool_name}({args})")
    answer = input("   Allow this? [y/N] ").strip().lower()
    return answer == "y"


def ask_password(tool_name: str, args: dict) -> str:
    print(f"\n🔒 The model wants to edit: {args.get('filename')} in {args.get('directory')}")
    if tool_name == "str_replace_in_file":
        old = args.get("old_str", "")
        new = args.get("new_str", "")
        print(f"   Replace:\n     {old[:200]!r}")
        print(f"   With:\n     {new[:200]!r}")
    else:
        preview = args.get("content", "")
        if preview:
            snippet = preview[:200] + ("..." if len(preview) > 200 else "")
            print(f"   New content preview: {snippet!r}")
    return getpass.getpass("   Enter password to approve this edit: ")


def run_tool_call(tool_call):
    name = tool_call.function.name
    args = tool_call.function.arguments
    if isinstance(args, str):
        args = json.loads(args)

    if name not in FUNCTION_MAP:
        return {"error": f"Unknown tool: {name}"}

    if name in PASSWORD_PROTECTED_TOOLS:
        args = {**args, "password": ask_password(name, args)}
    elif name in DESTRUCTIVE_TOOLS and not confirm(name, args):
        return {"error": "User declined to run this action."}

    try:
        return FUNCTION_MAP[name](**args)
    except TypeError as e:
        return {"error": f"Bad arguments for {name}: {e}"}


def chat_loop():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("Local File Agent (openai/gpt-oss-20b via Groq) — type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        # Keep letting the model call tools until it produces a plain reply
        while True:
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=4096,
                )
            except Exception as e:
                print(f"\n⚠️  Groq API error: {e}")
                print("   Try rephrasing the request as smaller steps (e.g. "
                      "'add a docstring to press_shortcut' rather than "
                      "'rewrite the whole file'), then try again.\n")
                break

            msg = response.choices[0].message

            # Groq's tool-calling requires the assistant message (including
            # tool_calls) to be echoed back verbatim in message history.
            messages.append(msg.model_dump(exclude_unset=True))

            if not msg.tool_calls:
                print(f"\nAgent: {(msg.content or '').strip()}\n")
                break

            for call in msg.tool_calls:
                result = run_tool_call(call)
                print(f"   -> {result}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                })


if __name__ == "__main__":
    chat_loop()

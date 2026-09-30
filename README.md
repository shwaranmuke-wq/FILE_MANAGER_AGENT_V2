# Local File Agent 🗂️

A terminal-based AI agent that manages files on your own machine using
plain English — powered by **Groq's free-tier API** running
**openai/gpt-oss-20b**, OpenAI's small open-weight model. Groq's inference
runs on custom LPU hardware (not GPU), so responses come back at roughly
1000 tokens/sec — no local model to load, no GPU/RAM needed on your
machine.

> **Note:** Groq retired `llama-3.1-8b-instant` from its free/developer
> tier on August 16, 2026. `openai/gpt-oss-20b` is Groq's own recommended
> replacement — it's free-tier, supports function calling, and is
> actually faster. If Groq changes its lineup again, check
> [console.groq.com/docs/models](https://console.groq.com/docs/models)
> for the current free-tier model list and swap the `MODEL` constant in
> `agent.py`.

Ask it things like:

> "List everything in my Downloads folder"
> "Create a folder called `invoices` on the Desktop and move all PDFs into it"
> "Rename `draft.txt` to `final.txt` in my current project folder"
> "Read `notes.md` and tell me what's in it"

The model plans, calls tools, reads the results, and keeps going until the
task is done — you approve any destructive action (delete, move, rename,
overwrite) before it runs.

## How it works

```
you type a request
      │
      ▼
openai/gpt-oss-20b (via Groq API) decides which tool to call
      │
      ▼
agent.py executes the matching Python function from tools.py
      │
      ▼
result goes back to the model → it decides the next step or replies
```

## Project structure

| File | Purpose |
|---|---|
| `agent.py` | Main chat loop — talks to Ollama, dispatches tool calls, asks for confirmation on risky actions |
| `tools.py` | The actual file-system operations (list, create, read, write, copy, move, rename, delete, mkdir) |
| `tool_schemas.py` | JSON-schema descriptions of each tool, so the model knows what it can call and with what arguments |
| `requirements.txt` | Python dependencies |

## Setup

### 1. Get a free Groq API key
Sign up at [console.groq.com/keys](https://console.groq.com/keys) and
create a key. The free tier easily covers this kind of usage.

### 2. Set the key as an environment variable
```bash
export GROQ_API_KEY="your-key-here"      # macOS/Linux (add to ~/.bashrc or ~/.zshrc to persist)
setx GROQ_API_KEY "your-key-here"        # Windows (open a new terminal after this)
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the agent
```bash
python agent.py
```

You'll get a prompt:

```
Local File Agent (openai/gpt-oss-20b via Groq) — type 'exit' to quit.

You: create a folder called test_run on the desktop
```

## Available tools

| Tool | What it does |
|---|---|
| `list_files(directory)` | List files/folders in a directory (max 100 entries) |
| `create_file(directory, filename)` | Create an empty file |
| `read_file(directory, filename)` | Read a file's text content |
| `write_file(directory, filename, content)` | Overwrite a file with new content |
| `remove_file(directory, filename)` | Delete a file |
| `rename_file(directory, old_name, new_name)` | Rename a file |
| `copy_file(source_directory, filename, destination_directory)` | Copy a file |
| `move_file(source_directory, filename, destination_directory)` | Move a file |
| `create_folder(directory, folder_name)` | Create a new folder |
| `open_file(directory, filename)` | Open a file in the OS default app (cross-platform) |
| `edit_file(directory, filename, content)` | 🔒 Overwrite an **existing** file's full content — requires a password entered locally |
| `str_replace_in_file(directory, filename, old_str, new_str)` | 🔒 Preferred way to edit existing files — replaces one exact, unique snippet without resending the whole file |
| `press_shortcut(combo, delay)` | Press a keyboard shortcut, e.g. `ctrl+c`, `alt+tab`, `win+d` |

## Safety notes

- **Confirmation prompts**: `remove_file`, `move_file`, `rename_file`,
  `write_file`, and `press_shortcut` always ask `[y/N]` in the terminal
  before executing, since these can destroy/overwrite data or affect
  whatever's on screen. You can remove tools from `DESTRUCTIVE_TOOLS` in
  `agent.py` if you want it fully autonomous — not recommended until you
  trust its behavior.
- **Password-protected editing**: `edit_file` and `str_replace_in_file`
  (changing the content of a file that already exists) require a
  password, currently `123`, defined as `EDIT_PASSWORD` at the top of
  `tools.py` — change it there whenever you like. Importantly, **the
  password is entered locally in your terminal** (via `getpass`, so it's
  hidden as you type) and is never sent to Groq — the model only ever
  asks for the edit; it never sees or supplies the password.
- **Editing large or existing files**: prefer `str_replace_in_file` over
  `edit_file` for anything beyond a short file or a full rewrite. Asking
  the model to retype an entire file as one string is slow, costs more
  tokens, and — on larger files — risks the model's own output getting
  cut off mid-file, which produces an invalid tool call and errors out
  the turn instead of writing anything. `str_replace_in_file` only sends
  the small snippet that's actually changing, so it doesn't hit this
  problem. The system prompt already nudges the model this way, but
  double-check what it's about to do before entering the password.
- **Editing the agent's own source files**: nothing stops you from
  asking the agent to modify `agent.py`, `tools.py`, or
  `tool_schemas.py` themselves. That works, but if an edit introduces a
  syntax error or breaks something, the *next* run of `python agent.py`
  will simply fail to start — there's no self-check here. Keep a backup
  (or a git commit) before letting it touch its own code.
- **`press_shortcut` caveat**: this actually presses keys on your
  machine via `pyautogui`. It affects whatever window currently has
  focus — same as if you pressed the keys yourself. Requires a graphical
  session (won't work over a headless SSH connection).
- **No sandboxing by default**: the agent can touch any path it's given
  and has permission to reach. If you want to restrict it to one folder
  (e.g. a `sandbox/` directory), the easiest change is to validate that
  `directory` in every tool call is inside an allowed root before running
  it — happy to add that if you want it locked down.
- **Small-model caveat**: gpt-oss-20b is fast and free but can
  occasionally misjudge multi-step plans or hallucinate a filename.
  Review what it's about to do, especially for delete/move requests, and
  keep backups of anything important.
- **Your files never leave your machine except as tool arguments**: the
  model only ever sees directory paths, filenames, and file contents you
  ask it to read/write — those do go over the network to Groq as part of
  the conversation, same as any cloud LLM API. If that's a concern for
  sensitive files, keep this agent restricted to non-sensitive folders.

## Extending it

To add a new capability:
1. Write the function in `tools.py` (return a plain dict).
2. Add its JSON-schema description to `TOOLS` in `tool_schemas.py`.
3. Register it in `FUNCTION_MAP` in `agent.py` (and in `DESTRUCTIVE_TOOLS`
   if it's risky).

That's it — the model will pick it up automatically on the next run.

## Troubleshooting

- **`SystemExit: GROQ_API_KEY is not set`**: the env var isn't visible to
  this terminal session. Re-run the `export`/`setx` command from Setup
  step 2, and for `setx` open a **new** terminal window afterward.
- **`AuthenticationError` from Groq**: the key is invalid, expired, or
  copied with extra whitespace — regenerate it at
  [console.groq.com/keys](https://console.groq.com/keys).
- **`RateLimitError`**: the free tier has generous but finite
  requests/tokens-per-minute limits. Wait a moment and retry, or check
  your usage at the Groq console.
- **`model_decommissioned` / "model not found"**: Groq periodically
  retires models (as happened to `llama-3.1-8b-instant` in Aug 2026).
  Check [console.groq.com/docs/models](https://console.groq.com/docs/models)
  for the current free-tier list and update `MODEL` in `agent.py`.
- **Model never calls tools, just talks**: rare with gpt-oss-20b, but if
  it happens, make the request more explicit (name the exact directory
  and action) — very small/ambiguous prompts sometimes get answered in
  prose instead of via a tool call.
- **`tool_use_failed` / "Failed to parse tool call arguments as JSON"**:
  the model's response got cut off mid-generation, usually because it
  tried to emit an entire large file as one `edit_file` argument. As of
  this version, that no longer crashes the program — the agent prints
  the error and asks you to retry. Prefer smaller, targeted edits ("add
  a docstring to `press_shortcut`") over "rewrite the whole file", and
  point the model at `str_replace_in_file` if it keeps defaulting to
  `edit_file` for big files.
- **`notepad.exe` error on `open_file`**: only relevant on Windows; on
  macOS/Linux it uses `open`/`xdg-open` automatically.

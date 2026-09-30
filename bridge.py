"""bridge.py — runs the agent loop from agent.py, but talks to Electron over
JSON lines (stdin/stdout) instead of the terminal. Approvals and passwords
are asked in the UI and passed straight to tools.py locally; the model never
sees them."""
import json
import os
import queue
import sys
import threading
import uuid

try:
    import agent
except SystemExit as e:
    print(json.dumps({"type": "fatal", "text": str(e)}), flush=True)
    sys.exit(1)

from tool_schemas import TOOLS

inbox = queue.Queue()


def reader():
    for line in sys.stdin:
        try:
            inbox.put(json.loads(line))
        except ValueError:
            pass
    inbox.put({"type": "quit"})


def send(**event):
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def ask(kind, name, args):
    rid = uuid.uuid4().hex
    send(type="approve", id=rid, kind=kind, tool=name, args=args)
    while True:
        m = inbox.get()
        if m.get("type") == "quit":
            sys.exit(0)
        if m.get("type") == "approval" and m.get("id") == rid:
            return m


def run_tool_call(name, raw_args):
    try:
        args = json.loads(raw_args) if raw_args else {}
    except ValueError:
        return name, {}, {"error": "Model sent invalid JSON arguments."}

    if name not in agent.FUNCTION_MAP:
        return name, args, {"error": f"Unknown tool: {name}"}

    call_args = dict(args)
    if name in agent.PASSWORD_PROTECTED_TOOLS:
        reply = ask("password", name, args)
        if not reply.get("allow"):
            return name, args, {"error": "User declined to run this action."}
        call_args["password"] = reply.get("password", "")
    elif name in agent.DESTRUCTIVE_TOOLS:
        if not ask("confirm", name, args).get("allow"):
            return name, args, {"error": "User declined to run this action."}

    try:
        return name, args, agent.FUNCTION_MAP[name](**call_args)
    except TypeError as e:
        return name, args, {"error": f"Bad arguments for {name}: {e}"}


def stream_reply(messages):
    """Stream one model response; push text to the UI as it arrives."""
    stream = agent.client.chat.completions.create(
        model=agent.MODEL, messages=messages, tools=TOOLS,
        tool_choice="auto", max_tokens=4096, stream=True,
        extra_body={"reasoning_effort": "low"},  # much faster than the default
    )
    text, calls = "", {}
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            text += delta.content
            send(type="delta", text=delta.content)
        for tc in delta.tool_calls or []:
            c = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
            if tc.id:
                c["id"] = tc.id
            if tc.function:
                if tc.function.name:
                    c["name"] += tc.function.name
                if tc.function.arguments:
                    c["arguments"] += tc.function.arguments
    return text, [calls[i] for i in sorted(calls)]


def turn(messages):
    while True:
        try:
            text, calls = stream_reply(messages)
        except Exception as e:
            send(type="assistant_end")
            send(type="error", text=f"Groq API error: {e}. Try smaller steps, then retry.")
            return

        if not text and not calls:
            send(type="delta", text="(no reply)")
        if text or not calls:
            send(type="assistant_end")

        entry = {"role": "assistant"}
        if text:
            entry["content"] = text
        if calls:
            for c in calls:
                c["id"] = c["id"] or "call_" + uuid.uuid4().hex[:8]
            entry["tool_calls"] = [
                {"id": c["id"], "type": "function",
                 "function": {"name": c["name"], "arguments": c["arguments"]}}
                for c in calls
            ]
        else:
            entry["content"] = text
        messages.append(entry)

        if not calls:
            return

        for c in calls:
            name, args, result = run_tool_call(c["name"], c["arguments"])
            send(type="tool", name=name, args=args, result=result)
            messages.append({"role": "tool", "tool_call_id": c["id"],
                             "content": json.dumps(result)})


def build_system():
    """System prompt + the user's saved memory (re-read every message, so edits apply instantly)."""
    prompt = agent.SYSTEM_PROMPT
    try:
        with open(os.environ.get("MEMORY_PATH", ""), encoding="utf-8") as f:
            memory = f.read().strip()[:4000]
    except OSError:
        memory = ""
    if memory:
        prompt += ("\nThe user's saved memory (notes they wrote themselves: paths, "
                   "preferences, context). Use it as background; the rules above "
                   "still take priority:\n" + memory + "\n")
    return prompt


def main():
    threading.Thread(target=reader, daemon=True).start()
    messages = [{"role": "system", "content": agent.SYSTEM_PROMPT}]
    send(type="ready", model=agent.MODEL)
    while True:
        m = inbox.get()
        kind = m.get("type")
        if kind == "quit":
            break
        if kind == "reset":
            messages = messages[:1]
        elif kind == "user" and m.get("text", "").strip():
            messages[0] = {"role": "system", "content": build_system()}
            messages.append({"role": "user", "content": m["text"].strip()})
            turn(messages)
        else:
            continue
        send(type="done")


if __name__ == "__main__":
    main()

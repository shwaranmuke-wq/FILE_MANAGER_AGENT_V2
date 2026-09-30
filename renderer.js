const $ = (id) => document.getElementById(id);
const log = $('log'), input = $('input'), sendBtn = $('send'), status = $('status');
const dialog = $('approval');

let busy = false;
let model = '';
let live = null; // assistant bubble currently streaming
let pending = null; // current approval request

function setReady(ready) {
  input.disabled = !ready || busy;
  sendBtn.disabled = !ready || busy;
  if (!input.disabled) input.focus();
}

function add(cls, text) {
  const el = document.createElement('div');
  el.className = 'msg ' + cls;
  el.textContent = text;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
  return el;
}

function addTool(ev) {
  const failed = ev.result && ev.result.error;
  const d = document.createElement('details');
  d.className = 'tool ' + (failed ? 'fail' : 'pass');
  const s = document.createElement('summary');
  const shown = ev.args && ev.args.content ? { ...ev.args, content: '…' } : ev.args;
  s.textContent = `${ev.name}(${JSON.stringify(shown)})`;
  const pre = document.createElement('pre');
  pre.textContent = JSON.stringify(ev.result, null, 2);
  d.append(s, pre);
  log.appendChild(d);
  log.scrollTop = log.scrollHeight;
}

function block(label, text) {
  const wrap = document.createElement('div');
  const l = document.createElement('label');
  l.textContent = label;
  const pre = document.createElement('pre');
  pre.textContent = text;
  wrap.append(l, pre);
  return wrap;
}

function showApproval(ev) {
  pending = ev;
  const a = ev.args || {};
  const body = $('ap-body');
  body.replaceChildren();
  const isPw = ev.kind === 'password';

  $('ap-title').textContent = isPw ? `Edit ${a.filename || 'file'}?` : `Run ${ev.tool}?`;
  $('ap-sub').textContent = a.directory
    ? `In ${a.directory}`
    : 'The agent wants to run this action on your computer.';

  if (ev.tool === 'str_replace_in_file') {
    body.append(block('Replace', a.old_str || ''), block('With', a.new_str || ''));
  } else if (ev.tool === 'edit_file' || ev.tool === 'write_file') {
    const c = a.content || '';
    body.append(block('New content', c.length > 600 ? c.slice(0, 600) + '…' : c));
  } else {
    body.append(block('Arguments', JSON.stringify(a, null, 2)));
  }

  $('ap-pw').hidden = !isPw;
  $('ap-pass').value = '';
  $('ap-allow').textContent = isPw ? 'Approve edit' : 'Allow';
  dialog.showModal();
  (isPw ? $('ap-pass') : $('ap-allow')).focus();
}

function answer(allow) {
  if (!pending) return;
  window.agent.send({
    type: 'approval',
    id: pending.id,
    allow,
    password: allow ? $('ap-pass').value : '',
  });
  pending = null;
  $('ap-pass').value = '';
  dialog.close();
}

$('ap-allow').addEventListener('click', () => answer(true));
$('ap-deny').addEventListener('click', () => answer(false));
$('ap-pass').addEventListener('keydown', (e) => { if (e.key === 'Enter') answer(true); });
dialog.addEventListener('cancel', (e) => { e.preventDefault(); answer(false); });

function submit() {
  const text = input.value.trim();
  if (!text || busy) return;
  add('user', text);
  input.value = '';
  busy = true;
  setReady(true);
  status.textContent = 'Working…';
  window.agent.send({ type: 'user', text });
}

$('composer').addEventListener('submit', (e) => { e.preventDefault(); submit(); });
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
});

$('reset').addEventListener('click', () => {
  if (pending) answer(false);
  log.replaceChildren();
  window.agent.send({ type: 'reset' });
});

$('savekey').addEventListener('click', () => {
  const key = $('key').value.trim();
  if (!key) return;
  $('keybar').classList.remove('show');
  $('key').value = '';
  status.textContent = 'Connecting…';
  window.agent.setKey(key);
});

$('memory-btn').addEventListener('click', async () => {
  $('mem-text').value = await window.agent.getMemory();
  $('memory').showModal();
  $('mem-text').focus();
});
$('mem-cancel').addEventListener('click', () => $('memory').close());
$('mem-save').addEventListener('click', async () => {
  await window.agent.setMemory($('mem-text').value);
  $('memory').close();
  add('note', 'Memory saved. The agent will use it from your next message.');
});

window.agent.onEvent((ev) => {
  switch (ev.type) {
    case 'need-key':
      status.classList.remove('live');
      status.textContent = 'Not connected';
      $('keybar').classList.add('show');
      $('key').focus();
      break;
    case 'ready':
      busy = false;
      status.classList.add('live');
      model = ev.model;
      status.textContent = model;
      setReady(true);
      break;
    case 'delta':
      if (!live) live = add('assistant', '');
      live.textContent += ev.text;
      log.scrollTop = log.scrollHeight;
      break;
    case 'assistant_end':
      live = null;
      break;
    case 'tool':
      addTool(ev);
      break;
    case 'approve':
      showApproval(ev);
      break;
    case 'error':
      add('error', ev.text);
      break;
    case 'fatal':
      add('error', ev.text);
      status.classList.remove('live');
      status.textContent = 'Stopped';
      setReady(false);
      break;
    case 'done':
      busy = false;
      status.textContent = model;
      setReady(true);
      break;
    case 'exit':
      status.classList.remove('live');
      status.textContent = 'Agent stopped';
      setReady(false);
      break;
  }
});

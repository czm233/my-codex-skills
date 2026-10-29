import { spawn } from 'node:child_process';
import { mkdir, open, appendFile, stat, rename, readdir, unlink, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join, dirname } from 'node:path';
import { homedir, hostname } from 'node:os';
import { fileURLToPath } from 'node:url';
export const name = 'bark-notifications';
export const inject = ['agents', 'sessionTitle'];
const here = dirname(fileURLToPath(import.meta.url));
/** Child sessions (subagent tool children and resident continuable children) never notify; only top-level user sessions do. */
export function isChildSession(header) {
  return !!header && (header.origin === 'subagent' || header.parentSession != null);
}
export function createHandler({ stateDir, send, diagnostic = async () => {}, enabled = true, getNotification = async () => null }) {
  return async ({ agent, turn }) => {
    try {
      const h = agent?.session?.header;
      if (!enabled || !h?.id || isChildSession(h) || !Number.isInteger(turn) || turn < 0) return;
      const notification = await getNotification(agent, turn);
      if (!notification?.session_title || !notification?.reply_preview) return;
      const hash = createHash('sha256').update(JSON.stringify([h.id, turn])).digest('hex');
      await mkdir(stateDir, { recursive: true });
      try { const f = await open(join(stateDir, hash), 'wx'); await f.close(); }
      catch (e) { if(e.code === 'EEXIST') return; throw e; }
      let result;
      try { result = await send(notification); } catch { result = { status: 'send_failed' }; }
      await diagnostic({ time: new Date().toISOString(), event: hash, status: result.status, http_status: result.http_status });
      const files = await readdir(stateDir);
      if (files.length > 2000) {
        const entries = await Promise.all(files.map(async name => ({ name, time: (await stat(join(stateDir,name))).mtimeMs })));
        entries.sort((a,b) => b.time-a.time);
        await Promise.all(entries.slice(1500).map(e => unlink(join(stateDir,e.name))));
      }
    } catch { /* Never interfere with the agent or retry a failed notification. */ }
  };
}
export function sendViaPowerShell(notification) {
  return new Promise(resolve => {
    const exe = join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe');
    const child = spawn(exe, ['-NoProfile', '-NonInteractive', '-File', join(here, 'send.ps1')], { windowsHide: true, stdio: ['pipe','pipe','ignore'], timeout: 12000 });
    child.stdin.on('error', () => {});
    child.stdin.end(JSON.stringify(notification));
    let output = ''; child.stdout.on('data', b => { if(output.length < 2048) output += b.toString(); });
    child.on('error', () => resolve({status:'sender_unavailable'}));
    child.on('close', () => {
      try { const v=JSON.parse(output.trim()); resolve({status:['accepted','send_failed','credential_unavailable'].includes(v.status)?v.status:'send_failed',http_status:Number.isInteger(v.http_status)?v.http_status:undefined}); }
      catch { resolve({status:'send_failed'}); }
    });
  });
}
export function normalizeText(raw, max) {
  if (typeof raw !== 'string') return '';
  return Array.from(raw.replace(/\p{C}/gu, ' ').replace(/\s+/gu, ' ').trim()).slice(0,max).join('');
}
export function replyPreview(message) {
  const text=(Array.isArray(message?.content)?message.content:[])
    .filter(b=>b.type==='text' && typeof b.text==='string').map(b=>b.text).join('');
  const safe=normalizeText(text,31);
  const chars=Array.from(safe);
  return chars.slice(0,30).join('')+(chars.length>30?'…':'');
}
// --- macOS (Bark over HTTPS POST; the device key never leaves this machine's keychain) ---
export const KEYCHAIN_SERVICE = 'codex-bark-notifications';
export const KEYCHAIN_ACCOUNT = 'codex';
export const BARK_PUSH_URL = 'https://api.day.app/push';
export function macStateRoot() { return join(homedir(), 'Library', 'Application Support', 'DSHBark'); }
export function stateRoot() {
  if (process.platform === 'win32') return join(process.env.LOCALAPPDATA, 'DSHBark');
  if (process.platform === 'darwin') return macStateRoot();
  return join(homedir(), '.local', 'state', 'DSHBark');
}
/** Read the Bark device key from the login keychain. Resolves null when absent; the value is never logged. */
export function readKeychainKey(service = KEYCHAIN_SERVICE, account = KEYCHAIN_ACCOUNT) {
  return new Promise(resolve => {
    const child = spawn('security', ['find-generic-password', '-s', service, '-a', account, '-w'], { stdio: ['ignore','pipe','ignore'] });
    let out = '';
    child.stdout.on('data', b => { if (out.length < 4096) out += b.toString('utf8'); });
    child.on('error', () => resolve(null));
    child.on('close', code => {
      const key = out.replace(/\r?\n$/, '');
      resolve(code === 0 && key !== '' ? key : null);
    });
  });
}
/** POST one Bark push. Resolves {status, http_status?}; never rejects, never exposes the key. */
export async function sendViaBarkPush({ title, body, sound, group = 'dsh', level = 'active', url }) {
  try {
    const device_key = await readKeychainKey();
    if (!device_key) return { status: 'credential_unavailable' };
    const payload = { device_key, title, body, group, level };
    if (sound) payload.sound = sound;
    if (url) payload.url = url;
    const res = await fetch(BARK_PUSH_URL, {
      method: 'POST',
      headers: { 'content-type': 'application/json; charset=utf-8' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(10000),
    });
    return { status: res.ok ? 'accepted' : 'send_failed', http_status: res.status };
  } catch { return { status: 'send_failed' }; }
}
/** Fire-and-forget macOS desktop notification. Failures are swallowed. */
export function notifyDesktop(title, body, sound = 'Glass') {
  try {
    if (process.platform !== 'darwin') return;
    const esc = s => String(s).replaceAll('\\','\\\\').replaceAll('"','\\"');
    spawn('osascript', ['-e', `display notification "${esc(body)}" with title "${esc(title)}" sound name "${esc(sound)}"`],
      { stdio: 'ignore', detached: true }).unref();
  } catch { /* desktop notification is best-effort */ }
}
export async function readLocalSettings(root) {
  try { const v = JSON.parse(await readFile(join(root, 'settings.json'), 'utf8')); return v && typeof v === 'object' ? v : {}; } catch { return {}; }
}
export function machineLabel(local) {
  return normalizeText(local.machine_label || hostname(), 24).replace(/\[/g,'(').replace(/\]/g,')') || 'Mac';
}
export function validSound(local, fallback) {
  return typeof local.sound === 'string' && /^[^/\\\p{C}]{1,120}$/u.test(local.sound) ? local.sound.trim() : fallback;
}
/** Fold one approval/request into a notification payload (pure; unit-tested). */
export function approvalNotification(req, local = {}) {
  const tool = typeof req?.tool === 'string' && req.tool !== '' ? req.tool : 'tool';
  const raw = typeof req?.displayReason === 'string' && req.displayReason !== '' ? req.displayReason
    : typeof req?.reason === 'string' ? req.reason : '';
  const reason = normalizeText(raw, 160);
  return {
    title: `${machineLabel(local)}｜等待审批`,
    body: reason === '' ? `工具 ${tool} 正在等待你的批准` : `${tool}：${reason}`,
    sound: validSound(local, 'bell'),
    group: 'dsh-approval',
    level: 'timeSensitive',
  };
}
export function apply(ctx, config = {}) {
  const root = stateRoot();
  if (process.platform === 'win32') {
    const replies = new WeakMap();
    ctx.on('session/event', (session,event) => {
      if(isChildSession(session.header)) return;
      if(event.type==='turn/start') replies.delete(session);
      if(event.type==='assistant/message') {
        replies.set(session,{turn:event.data.turn,preview:replyPreview(event.data.message)});
      }
    });
    const getNotification = async (agent,turn) => {
      const reply = replies.get(agent.session);
      if(reply?.turn!==turn || !reply.preview) return null;
      const title=normalizeText(ctx.sessionTitle.get(agent.session)?.title,120);
      if(!title || ['本轮回复已结束','本轮会话已结束'].includes(title)) return null;
      let local={};
      try { local=JSON.parse(await readFile(join(root,'settings.json'),'utf8')); } catch {}
      const label=normalizeText(local.machine_label || process.env.COMPUTERNAME || 'Windows',24).replace(/\[/g,'(').replace(/\]/g,')');
      const sound=validSound(local,'bell_quiet');
      return {session_title:title,reply_preview:reply.preview,machine_label:label,sound};
    };
    const diagnostic = async record => {
      const path = join(root,'diagnostics.jsonl');
      try { if ((await stat(path)).size > 262144) await rename(path,path+'.previous'); } catch {}
      await appendFile(path,JSON.stringify(record)+'\n');
    };
    ctx.on('agent/turn-stopping', createHandler({stateDir:join(root,'dedup'),send:sendViaPowerShell,diagnostic,enabled:config.enabled!==false,getNotification}));
    ctx.logger.info('Bark notification hook loaded (Windows)');
    return;
  }
  if (process.platform !== 'darwin') return;
  // --- macOS: turn-finished push + approval-waiting push & desktop notification ---
  const replies = new WeakMap();
  ctx.on('session/event', (session,event) => {
      if(isChildSession(session.header)) return;
    if(event.type==='turn/start') replies.delete(session);
    if(event.type==='assistant/message') replies.set(session,{turn:event.data.turn,preview:replyPreview(event.data.message)});
  });
  const diagnostic = async record => {
    const path = join(root,'diagnostics.jsonl');
    try { if ((await stat(path)).size > 262144) await rename(path,path+'.previous'); } catch {}
    await appendFile(path,JSON.stringify(record)+'\n');
  };
  const getNotification = async (agent,turn) => {
    const reply = replies.get(agent.session);
    if(reply?.turn!==turn || !reply.preview) return null;
    const title=normalizeText(ctx.sessionTitle.get(agent.session)?.title,120);
    if(!title || ['本轮回复已结束','本轮会话已结束'].includes(title)) return null;
    const local = await readLocalSettings(root);
    return {session_title:title,reply_preview:reply.preview,machine_label:machineLabel(local),sound:validSound(local,'bell_quiet')};
  };
  const push = notification => sendViaBarkPush({
    title: `${notification.machine_label}｜${notification.session_title}`,
    body: notification.reply_preview,
    sound: notification.sound,
    group: 'dsh',
  });
  ctx.on('agent/turn-stopping', createHandler({stateDir:join(root,'dedup'),send:push,diagnostic,enabled:config.enabled!==false,getNotification}));
  // Approval waiting: listen-only on the approval/request waterfall — notify, then pass through untouched.
  ctx.on('approval/request', (req, next) => {
    try {
      readLocalSettings(root).then(local => {
        if (local.desktop === false) return;
        const n = approvalNotification(req, local);
        notifyDesktop(n.title, n.body, 'Glass');
        return sendViaBarkPush(n);
      }).catch(() => {});
      const result = next();
      if (result && typeof result.then === 'function') {
        result.then(outcome => ({ outcome }), () => ({ outcome: 'unavailable' })).then(({ outcome }) => readLocalSettings(root)).then(local => {
          if (local.notify_answered === false) return;
          const tool = typeof req?.tool === 'string' && req.tool !== '' ? req.tool : 'tool';
          notifyDesktop(`${machineLabel(local)}｜审批已处理`, `${tool} → ${String(outcome)}`, 'Pop');
        }).catch(() => {});
      }
    } catch { /* listening must never affect the approval flow */ }
    return next();
  });
  ctx.logger.info('Bark notification hook loaded (macOS)');
}

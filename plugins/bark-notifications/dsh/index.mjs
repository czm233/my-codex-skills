import { spawn } from 'node:child_process';
import { mkdir, open, appendFile, stat, rename, readdir, unlink, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
export const name = 'bark-notifications';
export const inject = ['agents', 'sessionTitle'];
const here = dirname(fileURLToPath(import.meta.url));
export function createHandler({ stateDir, send, diagnostic = async () => {}, enabled = true, getNotification = async () => null }) {
  return async ({ agent, turn }) => {
    try {
      const h = agent?.session?.header;
      if (!enabled || !h?.id || h.origin === 'subagent' || !Number.isInteger(turn) || turn < 0) return;
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
export function apply(ctx, config = {}) {
  if (process.platform !== 'win32' && !process.env.LOCALAPPDATA) return;
  const root = join(process.env.LOCALAPPDATA, 'DSHBark');
  const replies = new WeakMap();
  ctx.on('session/event', (session,event) => {
    if(session.header.origin==='subagent') return;
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
    const sound=typeof local.sound==='string' && /^[^/\\\p{C}]{1,120}$/u.test(local.sound)?local.sound.trim():'bell_quiet';
    return {session_title:title,reply_preview:reply.preview,machine_label:label,sound};
  };
  const diagnostic = async record => {
    const path = join(root,'diagnostics.jsonl');
    try { if ((await stat(path)).size > 262144) await rename(path,path+'.previous'); } catch {}
    await appendFile(path,JSON.stringify(record)+'\n');
  };
  ctx.on('agent/turn-stopping', createHandler({stateDir:join(root,'dedup'),send:sendViaPowerShell,diagnostic,enabled:config.enabled!==false,getNotification}));
  ctx.logger.info('Bark notification hook loaded');
}

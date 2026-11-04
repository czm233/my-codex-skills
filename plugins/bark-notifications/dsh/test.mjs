import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHandler,apply,replyPreview,normalizeText,approvalNotification,resolveBarkConfig,barkPushUrl,normalizeBaseUrl,BARK_DEFAULTS,BARK_PUSH_URL,sendViaBarkPush,readKeychainKey,inspectBarkConfig,formatBarkConfig } from './index.mjs';
test('dedup, subagent exclusion, failure containment, no content access', async()=>{
 const root=await mkdtemp(join(tmpdir(),'dsh-bark-test-')); let calls=0;const records=[];
 try {
  const send=async()=>{calls++;return {status:'accepted',http_status:200}};
  const notification=async()=>({session_title:'test title',reply_preview:'done'});
  const make=()=>createHandler({stateDir:root,send,getNotification:notification,diagnostic:async r=>records.push(r)});
  const agent={session:{header:{id:'test'},get events(){throw Error('must not read')}}};
  await Promise.all([make()({agent,turn:1}),make()({agent,turn:1})]);assert.equal(calls,1);
  await make()({agent,turn:1});assert.equal(calls,1);
  await make()({agent:{session:{header:{id:'child',origin:'subagent'}}},turn:1});assert.equal(calls,1);
   await make()({agent:{session:{header:{id:'resident',parentSession:'p1'}}},turn:1});assert.equal(calls,1);
  await make()({agent,turn:2});assert.equal(calls,2);
  await createHandler({stateDir:root,send,getNotification:notification,enabled:false})({agent,turn:3});assert.equal(calls,2);
  await createHandler({stateDir:root,getNotification:notification,send:async()=>{throw Error('secret')}})({agent,turn:4});
  await make()({agent,turn:4});assert.equal(calls,2);
  assert.equal(JSON.stringify(records).includes('test'),false);
 }finally{await rm(root,{recursive:true,force:true})}
});
test('registers turn-stopping and approval/request listeners without calling senders',()=>{
 const events=[];
 apply({on:(e,h)=>{events.push(e);assert.equal(typeof h,'function')},logger:{info(){}},sessionTitle:{get(){}}});
 assert.ok(events.includes('agent/turn-stopping'));
 if (process.platform==='darwin') assert.ok(events.includes('approval/request')); // macOS-only approval listener
});

test('approval notification folding and passthrough',()=>{
 const n=approvalNotification({tool:'bash',reason:'  multi\nline   reason  '},{machine_label:'CZM-Mac'});
 assert.equal(n.title,'CZM-Mac｜等待审批');
 assert.equal(n.body,'bash：multi line reason');
 assert.equal(n.group,'dsh-approval');
 assert.equal(n.level,'timeSensitive');
 const minimal=approvalNotification({}, {});
 assert.equal(minimal.body,'工具 tool 正在等待你的批准');
 const long=approvalNotification({tool:'t',reason:'字'.repeat(200)},{});
 assert.equal(Array.from(long.body).length,162); // tool + '：' + 160 chars
});

test('Mac-compatible title and 30-character reply formatting',()=>{
 assert.equal(replyPreview({content:[{type:'thinking',text:'private'},{type:'text',text:'测试完成'}]}),'测试完成');
 assert.equal(replyPreview({content:[{type:'text',text:'你'.repeat(31)}]}),'你'.repeat(30)+'…');
 assert.equal(replyPreview({content:[{type:'text',text:'😀'.repeat(31)}]}),'😀'.repeat(30)+'…');
 assert.equal(normalizeText(' title\n   text ',120),'title text');
});
test('Windows sender input preserves Chinese JSON', {skip:process.platform!=='win32'}, async()=>{
 const {spawnSync}=await import('node:child_process');
 const {readFileSync}=await import('node:fs');
 const script=readFileSync(new URL('./send.ps1',import.meta.url),'utf8');
 const encoding=script.split(/\r?\n/).find(l=>l.startsWith('[Console]::InputEncoding'));
 assert.ok(encoding);
 const ps=`$ErrorActionPreference='Stop';[Console]::OutputEncoding=[Text.Encoding]::UTF8;${encoding};$n=[Console]::In.ReadToEnd()|ConvertFrom-Json;[Console]::Write($n.session_title)`;
 const r=spawnSync('powershell.exe',['-NoProfile','-NonInteractive','-EncodedCommand',Buffer.from(ps,'utf16le').toString('base64')],{input:JSON.stringify({session_title:'中文通知测试'}),encoding:'utf8',timeout:10000});
 assert.equal(r.status,0);assert.equal(r.stdout,'中文通知测试');
});

// --- Configurable base URL / keychain entry (defaults must stay byte-identical) ---
const withFetch = async (fn) => {
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(typeof url === 'string' ? url : url?.url ?? url), init });
    return { ok: true, status: 200 };
  };
  try { await fn(calls); } finally { globalThis.fetch = original; }
};
test('default config resolves to the historical values',()=>{
  const value=resolveBarkConfig({},{});
  assert.deepEqual({...value},{baseUrl:'https://api.day.app',baseUrlSource:'default',keychainService:'codex-bark-notifications',keychainServiceSource:'default',keychainAccount:'codex',keychainAccountSource:'default'});
  assert.equal(barkPushUrl(),'https://api.day.app/push');
  assert.equal(BARK_PUSH_URL,'https://api.day.app/push');
  assert.deepEqual({...BARK_DEFAULTS},{baseUrl:'https://api.day.app',keychainService:'codex-bark-notifications',keychainAccount:'codex'});
});
test('unconfigured push still goes to https://api.day.app/push with no bark override',async()=>{
  const key=await readKeychainKey();
  if(!key) return; // no local credential: the request path cannot be exercised
  await withFetch(async calls=>{
    const r=await sendViaBarkPush({title:'t',body:'b',sound:'bell'});
    assert.equal(r.status,'accepted');assert.equal(r.http_status,200);
    assert.equal(calls.length,1);
    assert.equal(calls[0].url,'https://api.day.app/push');
    assert.equal(calls[0].init.method,'POST');
    assert.deepEqual(Object.keys(JSON.parse(calls[0].init.body)),['device_key','title','body','group','level','sound']);
  });
});
test('configured base URL joins /push without double slashes',async()=>{
  for(const [input,expected] of [
    ['http://10.100.0.2:30137','http://10.100.0.2:30137/push'],
    ['http://10.100.0.2:30137/','http://10.100.0.2:30137/push'],
    ['http://10.100.0.2:30137//','http://10.100.0.2:30137/push'],
    ['http://10.100.0.2:30137/push','http://10.100.0.2:30137/push'],
    ['  http://10.100.0.2:30137/  ','http://10.100.0.2:30137/push'],
    ['https://bark.example.com/bark/','https://bark.example.com/bark/push'],
  ]) assert.equal(barkPushUrl(input),expected,input);
  assert.throws(()=>barkPushUrl('nonsense'),TypeError);
});
test('configured base URL is used by the sender',async()=>{
  if(!await readKeychainKey()) return;
  await withFetch(async calls=>{
    await sendViaBarkPush({title:'t',body:'b',bark:{baseUrl:'http://10.100.0.2:30137'}});
    assert.equal(calls[0].url,'http://10.100.0.2:30137/push');
  });
});
test('invalid base URLs are rejected and never silently sent elsewhere',()=>{
  for(const bad of ['', '   ', 'ftp://host', 'javascript:alert(1)', 'http://user:pw@host:1', 'http://host:1/push?x=1', 'not a url']) assert.equal(normalizeBaseUrl(bad),null,String(bad));
  assert.throws(()=>barkPushUrl('ftp://host'),TypeError);
  // invalid config falls through to the next source, eventually the default
  assert.equal(resolveBarkConfig({bark:{baseUrl:'ftp://bad'}},{}).baseUrlSource,'default');
  assert.equal(resolveBarkConfig({bark:{baseUrl:'ftp://bad'}},{bark_base_url:'http://10.100.0.2:30137'}).baseUrl,'http://10.100.0.2:30137');
});
test('configuration priority: plugin config > settings.json > default',()=>{
  const C={bark:{baseUrl:'http://cfg:1',keychainService:'svc-cfg',keychainAccount:'acct-cfg'}};
  const L={bark_base_url:'http://local:2',bark_keychain_service:'svc-local',bark_keychain_account:'acct-local'};
  const both=resolveBarkConfig(C,L);
  assert.equal(both.baseUrl,'http://cfg:1');assert.equal(both.baseUrlSource,'config');
  assert.equal(both.keychainService,'svc-cfg');assert.equal(both.keychainAccount,'acct-cfg');
  const localOnly=resolveBarkConfig({},L);
  assert.equal(localOnly.baseUrl,'http://local:2');assert.equal(localOnly.baseUrlSource,'settings');
  assert.equal(localOnly.keychainService,'svc-local');assert.equal(localOnly.keychainAccount,'acct-local');
  const partial=resolveBarkConfig({bark:{baseUrl:'http://cfg:1'}},L);
  assert.equal(partial.baseUrl,'http://cfg:1');assert.equal(partial.keychainService,'svc-local');
  // top-level config keys are still accepted, nested bark.* wins
  assert.equal(resolveBarkConfig({baseUrl:'http://top:3'},{}).baseUrl,'http://top:3');
  assert.equal(resolveBarkConfig({baseUrl:'http://top:3',bark:{baseUrl:'http://nested:4'}},{}).baseUrl,'http://nested:4');
});
test('inspect config is redacted and reports the source',async()=>{
  const root=await mkdtemp(join(tmpdir(),'dsh-bark-inspect-'));
  try{
    const d=await inspectBarkConfig({config:{},root});
    assert.equal(d.pushUrl,'https://api.day.app/push');assert.equal(d.baseUrlSource,'default');
    const text=formatBarkConfig(d);
    assert.match(text,/https:\/\/api\.day\.app\/push/);assert.match(text,/\(default\)/);
    const realKey=await readKeychainKey();
    if(realKey) assert.equal(text.includes(realKey),false);
    await import('node:fs/promises').then(fs=>fs.writeFile(join(root,'settings.json'),JSON.stringify({bark_base_url:'http://10.100.0.2:30137/'})));
    const d2=await inspectBarkConfig({config:{},root});
    assert.equal(d2.pushUrl,'http://10.100.0.2:30137/push');assert.equal(d2.baseUrlSource,'settings');
    const d3=await inspectBarkConfig({config:{bark:{baseUrl:'http://cfg:1'}},root});
    assert.equal(d3.pushUrl,'http://cfg:1/push');assert.equal(d3.baseUrlSource,'config');
  }finally{await rm(root,{recursive:true,force:true})}
});

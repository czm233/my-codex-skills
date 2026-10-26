import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHandler,apply,replyPreview,normalizeText } from './index.mjs';
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
  await make()({agent,turn:2});assert.equal(calls,2);
  await createHandler({stateDir:root,send,getNotification:notification,enabled:false})({agent,turn:3});assert.equal(calls,2);
  await createHandler({stateDir:root,getNotification:notification,send:async()=>{throw Error('secret')}})({agent,turn:4});
  await make()({agent,turn:4});assert.equal(calls,2);
  assert.equal(JSON.stringify(records).includes('test'),false);
 }finally{await rm(root,{recursive:true,force:true})}
});
test('registers stopping event without calling sender',()=>{
 const previous=process.env.LOCALAPPDATA;process.env.LOCALAPPDATA=tmpdir();
 let event;apply({on:(e,h)=>{event=e;assert.equal(typeof h,'function')},logger:{info(){}}});assert.equal(event,'agent/turn-stopping');
 if(previous===undefined) delete process.env.LOCALAPPDATA; else process.env.LOCALAPPDATA=previous;
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

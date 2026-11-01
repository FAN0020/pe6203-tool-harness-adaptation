import {chromium} from '/Users/fanysmacpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const folder=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(folder,'../../..');
const runtime=path.join(root,'.cache/slidev-render-v1'),work=path.join(runtime,'prefix-pilot-W02');
fs.mkdirSync(work);
const source=path.join(folder,'blind-artifacts/W02/slides.md'),copy=path.join(work,'slides.md');
fs.copyFileSync(source,copy);
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const fd=fs.openSync(path.join(folder,'render-W02-server.log'),'wx');
const server=spawn(path.join(root,'.cache/node-runtime/node_modules/node/bin/node'),[path.join(runtime,'node_modules/@slidev/cli/bin/slidev.mjs'),copy,'--port','4785','--log','info'],{cwd:runtime,stdio:['ignore',fd,fd]});
const browser=await chromium.launch(),page=await browser.newPage({viewport:{width:1280,height:800}});
const errors=[],result={source_sha256:hash(source),copy_sha256:hash(copy),artifact_modified:false};
page.on('pageerror',e=>errors.push(String(e)));
try {
  for(let i=0;i<80;i++){try{if((await fetch('http://localhost:4785/')).ok)break;}catch{}await new Promise(r=>setTimeout(r,250));}
  await page.goto('http://localhost:4785/1',{waitUntil:'networkidle',timeout:30000});
  const layout=page.locator('.slidev-layout:visible').first();await layout.waitFor();
  result.dom=await layout.evaluate(e=>({text:e.innerText,background:getComputedStyle(e).backgroundColor,color:getComputedStyle(e).color,height:e.clientHeight,scrollHeight:e.scrollHeight,bodyText:document.body.innerText,images:[...document.images].map(i=>({src:i.src,complete:i.complete,naturalWidth:i.naturalWidth}))}));
  await page.screenshot({path:path.join(folder,'render-W02.png')});
}catch(e){result.error=String(e);}finally{
  result.consoleErrors=errors;result.unchanged=hash(source)===hash(copy);
  fs.writeFileSync(path.join(folder,'render-W02.json'),JSON.stringify(result,null,2)+'\n');
  await browser.close();server.kill('SIGTERM');
  await new Promise(r=>server.exitCode!==null?r():server.once('exit',r));fs.closeSync(fd);
}
console.log(JSON.stringify(result));

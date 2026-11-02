import {chromium} from '/Users/fanysmacpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';
import {fileURLToPath, pathToFileURL} from 'node:url';
const folder=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(folder,'../../..');
const episode=process.argv[2];if(!/^E0[1-4]$/.test(episode))throw Error('fixed episode required');
const runtime=path.join(root,'.cache/slidev-render-v1'),work=path.join(runtime,`experience-training-${episode}`);
const packet=JSON.parse(fs.readFileSync(path.join(folder,`review-inputs/${episode}.json`)));
const artifacts=packet.artifacts.filter(a=>a.path.endsWith('slides.md'));
if(artifacts.length!==1)throw Error('Need one persisted deck; retain ambiguity for manual review');
fs.mkdirSync(work);
const source=path.join(folder,'review-artifacts',episode,artifacts[0].path),copy=path.join(work,'slides.md');
fs.copyFileSync(source,copy);
const css=path.join(path.dirname(source),'theme.css');if(fs.existsSync(css))fs.copyFileSync(css,path.join(work,'theme.css'));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const {parseSync}=await import(pathToFileURL(path.join(runtime,'node_modules/@slidev/parser/dist/index.mjs')));
const parsed=parseSync(fs.readFileSync(copy,'utf8'),copy);
const result={episode,source_sha256:hash(source),copy_sha256:hash(copy),artifact_modified:false,page_count:parsed.slides.length,
  parsed_pages:parsed.slides.map(s=>({content:s.content,frontmatter:s.frontmatter})),pages:[]};
const fd=fs.openSync(path.join(folder,`render-${episode}-server.log`),'wx');
const server=spawn(path.join(root,'.cache/node-runtime/node_modules/node/bin/node'),[path.join(runtime,'node_modules/@slidev/cli/bin/slidev.mjs'),copy,'--port','4785','--log','info'],{cwd:runtime,stdio:['ignore',fd,fd]});
const browser=await chromium.launch(),page=await browser.newPage({viewport:{width:1280,height:800}}),errors=[];
page.on('pageerror',e=>errors.push(String(e)));
try {
  for(let i=0;i<80;i++){try{if((await fetch('http://localhost:4785/')).ok)break;}catch{}if(server.exitCode!==null)throw Error(`renderer exited ${server.exitCode}`);await new Promise(r=>setTimeout(r,250));}
  for(let n=1;n<=parsed.slides.length;n++){
    await page.goto(`http://localhost:4785/${n}`,{waitUntil:'networkidle',timeout:30000});
    const layout=page.locator('.slidev-layout:visible').first();await layout.waitFor();
    const dom=await layout.evaluate(e=>({text:e.innerText,background:getComputedStyle(e).backgroundColor,color:getComputedStyle(e).color,
      height:e.clientHeight,width:e.clientWidth,scrollHeight:e.scrollHeight,scrollWidth:e.scrollWidth,
      images:[...document.images].map(i=>({src:i.src,complete:i.complete,naturalWidth:i.naturalWidth}))}));
    const screenshot=`render-${episode}-${n}.png`;await page.screenshot({path:path.join(folder,screenshot)});
    result.pages.push({page:n,dom,screenshot});
  }
}catch(e){result.error=String(e);}finally{
  result.consoleErrors=errors;result.unchanged=hash(source)===hash(copy);
  fs.writeFileSync(path.join(folder,`render-${episode}.json`),JSON.stringify(result,null,2)+'\n');
  await browser.close();server.kill('SIGTERM');
  if(server.exitCode===null)await new Promise(r=>server.once('exit',r));fs.closeSync(fd);
}
console.log(JSON.stringify({episode,pages:result.page_count,rendered:result.pages.length,error:result.error,unchanged:result.unchanged}));

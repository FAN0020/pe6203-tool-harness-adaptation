import { chromium } from '/Users/fanysmacpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const folder = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(folder, '../../..');
const runtime = path.join(root, '.cache/slidev-render-v1');
const node = path.join(root, '.cache/node-runtime/node_modules/node/bin/node');
const sha = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const cases = JSON.parse(fs.readFileSync(path.join(folder, 'cases.json')));
const dest = path.join(folder, 'render-v2');
fs.mkdirSync(dest); // no silent reruns/overwrite
const browser = await chromium.launch({headless:true});
const results = [];
const inputs = [];
try {
  for (const stage of ['middle', 'late']) for (const name of ['train', 'heldout']) {
    const source = path.join(folder, 'workspaces', stage, name, 'slides.md');
    const working = path.join(runtime, `prefix-admission-v2-${stage}-${name}`);
    fs.mkdirSync(working);
    const copy = path.join(working, 'slides.md');
    fs.copyFileSync(source, copy);
    inputs.push({stage, name, source, copy, source_sha256:sha(source), copy_sha256:sha(copy)});
    const log = fs.openSync(path.join(dest, `${stage}-${name}-server.log`), 'wx');
    const server = spawn(node, [path.join(runtime, 'node_modules/@slidev/cli/bin/slidev.mjs'), copy, '--port', '4785', '--log', 'info'],
      {cwd:runtime, env:{...process.env, BROWSER:'none'}, stdio:['ignore', log, log]});
    const page = await browser.newPage({viewport:{width:1280,height:800}});
    const consoleErrors = [];
    page.on('pageerror', error => consoleErrors.push(String(error)));
    try {
      let ready = false;
      for (let attempt=0; attempt<80; attempt++) {
        try { ready = (await fetch('http://localhost:4785/')).ok; } catch {}
        if (ready) break;
        await new Promise(resolve => setTimeout(resolve,250));
      }
      if (!ready) throw Error('Slidev server unavailable');
      for (const entry of cases[name]) {
        const number = entry.index+1;
        await page.goto(`http://localhost:4785/${number}`, {waitUntil:'networkidle', timeout:30000});
        const canary = entry.body.match(/CANARY_\w+=\d+/)[0];
        const layout = page.locator('.slidev-layout:visible').filter({hasText:canary}).first();
        await layout.waitFor({state:'visible',timeout:15000});
        await page.evaluate(() => document.fonts.ready);
        const dom = await layout.evaluate(element => {
          const r=element.getBoundingClientRect(), css=getComputedStyle(element);
          const overflow = [...element.querySelectorAll('h1,h2,h3,p,li,table,pre')].filter(x => {
            const s=x.getBoundingClientRect();
            return s.width && s.height && (s.left<r.left-2 || s.right>r.right+2 || s.top<r.top-2 || s.bottom>r.bottom+2);
          }).map(x=>({tag:x.tagName,text:x.textContent}));
          return {text:element.innerText,background:css.backgroundColor,color:css.color,
            width:r.width,height:r.height,scrollHeight:element.scrollHeight,clientHeight:element.clientHeight,overflow};
        });
        const screenshot = `${stage}-${name}-${number}.png`;
        await page.screenshot({path:path.join(dest,screenshot)});
        const pass = dom.text.includes(canary) && dom.background==='rgb(15, 23, 42)' &&
          dom.color==='rgb(243, 244, 246)' && dom.overflow.length===0 && dom.scrollHeight<=dom.clientHeight+2 && consoleErrors.length===0;
        results.push({stage,name,page:number,canary,dom,screenshot,screenshot_sha256:sha(path.join(dest,screenshot)),consoleErrors:[...consoleErrors],pass});
      }
      if (sha(source)!==sha(copy)) throw Error('Render copy modified');
    } catch (error) {
      results.push({stage,name,pass:false,error:String(error),consoleErrors});
    } finally {
      await page.close();
      server.kill('SIGTERM');
      await new Promise(resolve => server.exitCode!==null ? resolve() : server.once('exit',resolve));
      fs.closeSync(log);
    }
  }
} finally {
  await browser.close();
  fs.writeFileSync(path.join(dest,'inputs.json'),JSON.stringify(inputs,null,2)+'\n');
  fs.writeFileSync(path.join(dest,'results.json'),JSON.stringify(results,null,2)+'\n');
}
console.log(JSON.stringify({pages:results.filter(r=>r.page).length,pass:results.length===18 && results.every(r=>r.pass),failures:results.filter(r=>!r.pass)}));

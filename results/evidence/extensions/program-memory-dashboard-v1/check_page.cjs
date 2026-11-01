// Evaluate the frozen browser properties without editing an agent artifact.
const fs = require('fs');
const path = require('path');
const http = require('http');
const {chromium} = require('/Users/fanysmacpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const [workspace, oraclePath, output] = process.argv.slice(2);
fs.mkdirSync(output, {recursive:false});
const expected = JSON.parse(fs.readFileSync(oraclePath, 'utf8'));
const publicRoot = path.resolve(workspace, 'public');
const checker = eval('(' + fs.readFileSync(path.resolve('experiments/extensions/program-memory-dashboard-v1/browser-check.js'),'utf8') + ')');
let mutation = false;
const changed = structuredClone(expected);
changed.daily[0].errors += 1;
changed.total_errors += 1;
changed.busiest_day = [...changed.daily].sort((a,b)=>b.errors-a.errors || a.date.localeCompare(b.date))[0].date;
const requests=[];
const server=http.createServer((req,res)=>{
  const pathname = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  requests.push({path:pathname, mutation});
  if(mutation && pathname==='/data.json') {res.setHeader('Content-Type','application/json');res.end(JSON.stringify(changed));return;}
  const filename=path.resolve(publicRoot,'.'+(pathname==='/'?'/index.html':pathname));
  if(!filename.startsWith(publicRoot+path.sep)) {res.statusCode=403;res.end();return;}
  try {const data=fs.readFileSync(filename);res.setHeader('Content-Type',({'html':'text/html','js':'text/javascript','css':'text/css','json':'application/json','svg':'image/svg+xml'})[filename.split('.').at(-1)]||'application/octet-stream');res.end(data);}
  catch {res.statusCode=404;res.end('Not found');}
});
function checks(result,want) {
 const rows=result.dom.rows;
 const daily=rows.length===want.daily.length && rows.every((r,i)=>r.date===want.daily[i].date && r.cells.length===2 && r.cells[0].trim()===want.daily[i].date && r.cells[1].trim()===String(want.daily[i].errors));
 const cards=['total_errors','days_covered','busiest_day'].every(key=>{
  const matches=result.dom.cards.filter(c=>c.key===key);
  if(matches.length!==1) return false;
  const c=matches[0], value=String(want[key]);
  const correct=key==='busiest_day'?c.text.includes(value):new RegExp('(^|[^0-9])'+value+'([^0-9]|$)').test(c.text);
  const highlighted=(c.background!=='rgba(0, 0, 0, 0)' && c.background!=='transparent')||parseFloat(c.border)>0;
  return correct && c.visible && highlighted;
 });
 const title=result.dom.title.some((t,i)=>t.visible && (t.animations>0 || t.text!==result.first[i]?.text));
 return {daily, cards, dynamic_title:title, no_fatal_errors:result.errors.length===0, no_horizontal_overflow:!result.dom.overflow};
}
(async()=>{
 let browser;
 const result={runs:[],passed:false,requests};
 try {
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  browser=await chromium.launch({headless:true});
  for(const mode of ['original','mutation']) {
   mutation=mode==='mutation';
   for(const viewport of [{width:1280,height:900},{width:390,height:844}]) {
    const page=await browser.newPage({viewport});
    await page.goto(`http://127.0.0.1:${server.address().port}/`,{waitUntil:'networkidle',timeout:30000});
    const measured=await checker(page);const properties=checks(measured,mutation?changed:expected);
    await page.screenshot({path:path.join(output,mode+'-'+viewport.width+'.png'),fullPage:true});
    result.runs.push({mode,measured,properties,passed:Object.values(properties).every(Boolean)});
    await page.close();
   }
  }
  result.runtime_data_fetch=['original','mutation'].every(mode=>requests.some(r=>r.path==='/data.json' && r.mutation===(mode==='mutation')));
  result.passed=result.runs.length===4 && result.runs.every(r=>r.passed) && result.runtime_data_fetch;
 } catch(error) {result.error=String(error);}
 finally {if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));fs.writeFileSync(path.join(output,'page-check.json'),JSON.stringify(result,null,2)+'\n');}
 console.log(JSON.stringify({passed:result.passed,runs:result.runs.map(r=>({mode:r.mode,viewport:r.measured.viewport,properties:r.properties})),error:result.error}));
})().catch(e=>{console.error(e);process.exitCode=1});

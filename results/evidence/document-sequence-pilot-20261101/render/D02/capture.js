async (page) => {
 const blocked=[]; const errors=[];
 await page.route('**/*',route=>{const u=new URL(route.request().url());if(['127.0.0.1','localhost'].includes(u.hostname)||u.protocol==='data:')return route.continue();blocked.push(u.origin);return route.abort();});
 page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:1440,height:900});
 const rows=[];
 for(let n=1;n<=1;n++){
  await page.goto('http://localhost:4802/'+n+'?clicks=99',{waitUntil:'networkidle'});
  await page.locator('.slidev-layout:visible').first().waitFor();
  await page.screenshot({path:'results/evidence/document-sequence-pilot-20261101/render/D02/page'+String(n).padStart(2,'0')+'.png'});
  rows.push(await page.evaluate((n)=>({page:n,title:document.title,body:document.body.innerText,layouts:Array.from(document.querySelectorAll('.slidev-layout')).filter(e=>e.getBoundingClientRect().width>0).map(e=>{const s=getComputedStyle(e);return {text:e.innerText,background:s.backgroundColor,color:s.color,width:e.clientWidth,height:e.clientHeight,scrollWidth:e.scrollWidth,scrollHeight:e.scrollHeight}})}),n));
 }
 return {rows,blocked:[...new Set(blocked)],errors};
}

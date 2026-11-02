const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {chromium} = require('/Users/fanysmacpro/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const [root, output] = process.argv.slice(2);
const assert = (ok, message) => {if (!ok) throw new Error(message)};
(async()=>{
  const server = http.createServer((req,res)=>{
    const file = path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname.replace(/\/$/,'/index.html'));
    if (!file.startsWith(root+path.sep) || !fs.existsSync(file)) {res.writeHead(404);res.end();return}
    const mime = file.endsWith('.css')?'text/css':file.endsWith('.js')?'application/javascript':'text/html';
    res.writeHead(200,{'content-type':mime});res.end(fs.readFileSync(file));
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const browser = await chromium.launch({headless:true});
  const evidence = {views:[],errors:[],externalRequests:[],negativeControl:false,passed:false};
  try {
    const page=await browser.newPage();
    page.on('pageerror',error=>evidence.errors.push(String(error)));
    await page.route('**/*',route=>{
      if(new URL(route.request().url()).hostname!=='127.0.0.1') {evidence.externalRequests.push(route.request().url());return route.abort()}
      return route.continue();
    });
    const url='http://127.0.0.1:'+server.address().port;
    const snapshot=()=>page.evaluate(()=>{
      const g=document.querySelector('[data-testid="gradient"]');
      const m=[...document.querySelectorAll('[data-testid="meteor-container"] > span')];
      const s=getComputedStyle(g);
      return {gradient:s.backgroundImage,position:s.backgroundPosition,gradientAnimations:g.getAnimations().length,
        text:g.textContent,visible:g.getBoundingClientRect().width>0 && g.getBoundingClientRect().height>0,
        meteorCount:m.length,meteorAnimations:m.map(n=>n.getAnimations().length),transforms:m.map(n=>getComputedStyle(n).transform)};
    });
    for(const viewport of [{width:1280,height:900},{width:390,height:844}]) {
      await page.setViewportSize(viewport);await page.goto(url,{waitUntil:'networkidle'});
      const a=await snapshot();await page.waitForTimeout(300);const b=await snapshot();
      assert(a.visible && a.text==='Reusable memory canary','gradient text not visible');
      assert(a.gradient.includes('gradient') && a.gradientAnimations>0 && a.position!==b.position,'gradient not animated');
      assert(a.meteorCount===7 && a.meteorAnimations.every(n=>n>0),'meteor count/animations wrong');
      assert(a.transforms.some((x,i)=>x!==b.transforms[i]),'meteor transforms did not change');
      evidence.views.push({viewport,before:a,after:b});
      await page.screenshot({path:path.join(output,'canary-'+viewport.width+'.png')});
    }
    await page.goto(url+'?count=0&from=%2300ff00&to=%23ff00ff',{waitUntil:'networkidle'});
    const modified=await snapshot();
    assert(modified.meteorCount===0 && modified.gradient!==evidence.views[0].before.gradient,'property mutation not reflected');
    evidence.propMutation=modified;
    await page.addStyleTag({content:'*{animation:none!important;transition:none!important}'});
    const negative=await snapshot();
    assert(negative.gradientAnimations===0,'negative control did not remove animation');
    evidence.negativeControl=true;evidence.negativeSnapshot=negative;
    assert(evidence.errors.length===0 && evidence.externalRequests.length===0,'page errors or external dependency');
    evidence.passed=true;
  } catch(error) {evidence.failure=String(error);process.exitCode=1}
  finally {
    fs.writeFileSync(path.join(output,'render-result.json'),JSON.stringify(evidence,null,2)+'\n');
    console.log(JSON.stringify({passed:evidence.passed,views:evidence.views.length,negativeControl:evidence.negativeControl,failure:evidence.failure}));
    await browser.close();await new Promise(resolve=>server.close(resolve));
  }
})();

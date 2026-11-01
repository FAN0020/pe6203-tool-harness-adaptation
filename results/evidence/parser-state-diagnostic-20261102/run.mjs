import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const base=path.dirname(new URL(import.meta.url).pathname);
const plan=JSON.parse(fs.readFileSync(path.join(base,'plan.json')));
for(const [file,expected] of Object.entries(plan.source_sha256)) {
 if(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')!==expected) throw new Error('Source hash mismatch');
}
const rows=[];
for(const stage of plan.stages) {
 const {GrammarParser}=await import(pathToFileURL(path.resolve('.cache/mcpevol',stage,'node_modules/math-mcp/dist/grammar-parser.js')));
 for(const [sequence,inputs] of Object.entries(plan.sequences)) {
  const parser=new GrammarParser();
  for(const [step,input] of inputs.entries()) {
   let result;
   try { const r=parser.parse(input); result={isValid:r.isValid,errors:JSON.parse(JSON.stringify(r.errors))}; }
   catch(e) {result={thrown:e.name,message:e.message};}
   rows.push({stage,sequence,step,input,result});
  }
 }
}
fs.writeFileSync(path.join(base,'results.json'),JSON.stringify({plan_sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(base,'plan.json'))).digest('hex'),rows},null,2)+'\n');
console.log(JSON.stringify(rows));

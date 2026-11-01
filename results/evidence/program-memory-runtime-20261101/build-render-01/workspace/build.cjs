// Common build support: identical for SP and candidate; creates no task content.
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const runtime = JSON.parse(fs.readFileSync(path.join(__dirname,'runtime.json'),'utf8'));
const dependencies = path.join(runtime.dependency_root,'node_modules');
const workspace = process.cwd();
const esbuild = require(path.join(dependencies,'esbuild'));
fs.mkdirSync(path.join(workspace,'public'),{recursive:true});
esbuild.buildSync({
  entryPoints:[path.join(workspace,'src/main.tsx')],
  outfile:path.join(workspace,'public/app.js'),
  bundle:true,platform:'browser',format:'iife',jsx:'automatic',
  alias:{'@':path.join(workspace,'src')},nodePaths:[dependencies],
  define:{'process.env.NODE_ENV':'"production"'},logLevel:'warning'
});
const input=fs.readFileSync(path.join(workspace,'styles.css'),'utf8')
  .replace('@import "tailwindcss"',`@import "${path.join(dependencies,'tailwindcss/index.css')}"`);
const temporary=path.join(workspace,'.runtime-styles.css');
fs.writeFileSync(temporary,input);
execFileSync(runtime.node,[path.join(dependencies,'@tailwindcss/cli/dist/index.mjs'),
  '-i',temporary,'-o',path.join(workspace,'public/styles.css'),'--minify'],{cwd:workspace,stdio:'inherit'});
console.log('Built public/app.js and public/styles.css; HTML, data and application content are supplied by the workspace author.');

'use strict';
const {spawn}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const root=path.resolve(__dirname,'..');
const nodeTests=['cloud_sync_test.js','cloud_integration_test.js','cloud_password_test.js',
  'cloud_account_race_test.js','reading_theme_tokens_v1.js','service_worker_v2_test.js'];
const browserTests=['browser_regression_v7.js','status_regression_v8.js','browser_layout_v11.js',
  'browser_v12_layout.js','browser_cloud_sync.js','browser_cloud_email.js','browser_cloud_password.js',
  'browser_reading_theme_v1.js','browser_pwa_offline_final.js','browser_v2_upgrade.js'];
async function run(file,syntax=false){
  await new Promise((resolve,reject)=>{
    const child=spawn(process.execPath,syntax?['--check',file]:[file],{cwd:root,stdio:'inherit'});
    const timer=setTimeout(()=>{child.kill();reject(Error('Timeout: '+file));},180000);
    child.on('error',error=>{clearTimeout(timer);reject(error);});
    child.on('exit',code=>{clearTimeout(timer);code===0?resolve():reject(Error(file+' exited '+code));});
  });
}
(async()=>{
  const browsers=process.argv.includes('--browser');
  let server;
  try{
    if(browsers){
      const site=path.join(root,'site');
      server=http.createServer((req,res)=>{
        const relative=decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/^\//,'')||'index.html';
        const target=path.resolve(site,relative);
        if(!target.startsWith(site+path.sep)){res.writeHead(403).end();return;}
        const mime={'.html':'text/html; charset=utf-8','.js':'application/javascript','.json':'application/json',
          '.css':'text/css','.webmanifest':'application/manifest+json','.png':'image/png','.svg':'image/svg+xml'};
        fs.readFile(target,(err,data)=>{if(err){res.writeHead(404).end();return;}
          res.writeHead(200,{'Content-Type':mime[path.extname(target)]||'application/octet-stream','Cache-Control':'no-store'}).end(data);});
      });
      await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(8765,'127.0.0.1',resolve);});
    }else{
      for(const name of fs.readdirSync(path.join(root,'site')).filter(f=>f.endsWith('.js')))await run('site/'+name,true);
      for(const name of fs.readdirSync(__dirname).filter(f=>f.endsWith('.js')))await run('tests/'+name,true);
    }
    for(const test of browsers?browserTests:nodeTests)await run('tests/'+test);
    console.log('PASS: '+(browsers?'all browser':'all Node/JS')+' suites completed');
  }finally{if(server)await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});

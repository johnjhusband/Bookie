const { chromium } = require('playwright');
const fs=require('fs'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const log=m=>console.log('[qbo] '+m);
(async()=>{
  const b=await chromium.launch({headless:true,args:['--no-sandbox']});
  const ctx=await b.newContext({storageState:'.intuit-session.json',userAgent:'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',viewport:{width:1400,height:1700}});
  const pg=await ctx.newPage();
  await pg.goto('https://qbo.intuit.com',{waitUntil:'domcontentloaded',timeout:60000}).catch(()=>{});
  let last='';
  for(let i=0;i<40;i++){
    await sleep(2500);
    const url=pg.url();
    if(/qbo\.intuit\.com\/app/.test(url) && !/sign-in|mfdloading/i.test(url)){ log('reached /app'); break; }
    if(/mfdloading/i.test(url)) continue;
    let body=''; try{body=(await pg.evaluate(()=>document.body.innerText)).toLowerCase();}catch(e){continue;}
    const state = body.includes("verify it's you")?'mfa':
      (body.includes('enter your')&&body.includes('password'))?'pw':
      body.includes("let's get you in")?'picker':
      body.includes('skip for now')?'skip':
      (body.includes('choose a company')||body.includes('which company'))?'company':'other';
    if(state!==last){log('state: '+state);last=state;}
    try{
      if(state==='picker'){ await pg.getByText('john@husband.llc').first().click({timeout:5000}); await sleep(4000); }
      else if(state==='pw'){
        for(const loc of [pg.getByLabel('Password'),pg.locator('input[type=password]'),pg.getByRole('textbox')]){try{if(await loc.count()){await loc.first().fill(process.env.INTUIT_PASS,{timeout:5000});break;}}catch(e){}}
        const cb=pg.getByRole('button',{name:/continue|sign in/i}).first(); if(await cb.count())await cb.click(); else await pg.keyboard.press('Enter'); await sleep(6000);
      }
      else if(state==='mfa'){
        const tb=pg.getByRole('button',{name:/text a code/i}).first(); if(await tb.count()){await tb.click();await sleep(5000);}
        log('NEED_CODE'); let code=null;
        for(let j=0;j<300;j++){if(fs.existsSync('/tmp/intuit-code.txt')){code=fs.readFileSync('/tmp/intuit-code.txt','utf8').trim();if(code)break;}await sleep(1500);}
        if(code){for(const loc of [pg.getByRole('textbox'),pg.locator('input[autocomplete="one-time-code"]')]){try{if(await loc.count()){await loc.first().fill(code,{timeout:5000});break;}}catch(e){}}
          const vb=pg.getByRole('button',{name:/continue|verify|sign in/i}).first(); if(await vb.count())await vb.click(); else await pg.keyboard.press('Enter'); await sleep(6000); try{fs.unlinkSync('/tmp/intuit-code.txt');}catch(e){}}
      }
      else if(state==='skip'){ await pg.getByText(/skip for now/i).first().click({timeout:4000}); await sleep(3000); }
      else if(state==='company'){ try{await pg.getByText(/husband/i).first().click({timeout:5000});await sleep(5000);}catch(e){log('company pick failed');} }
      else { await sleep(2000); }
    }catch(e){ log(state+' action err: '+String(e).slice(0,50)); }
  }
  await sleep(5000);
  await ctx.storageState({path:'.intuit-session.json'});
  await pg.screenshot({path:'qbo-dash.png',fullPage:false}).catch(()=>{});
  log('FINAL URL: '+pg.url().slice(0,150));
  log('TITLE: '+(((await pg.title())||'').slice(0,90)));
  const txt=await pg.evaluate(()=>document.body.innerText.replace(/\n{2,}/g,'\n').slice(0,700));
  log('PAGE:\n'+txt);
  log(/qbo\.intuit\.com\/app/.test(pg.url())&&!/sign-in/i.test(pg.url())?'>>> IN QBO COMPANY':'>>> NOT IN');
  await b.close();
})();

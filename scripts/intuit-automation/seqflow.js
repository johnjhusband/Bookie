const { chromium } = require('playwright');
const fs=require('fs'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let n=0; const log=m=>console.log('[seq] '+m);

// settle(): block until the page is actually RENDERED, not just on a timer.
// Waits for network to go idle, the URL to leave any loading shim, the body to
// carry real text, and any full-screen spinner to disappear. Returns the body text.
async function settle(pg,{timeout=20000}={}){
  const start=Date.now();
  // brief networkidle attempt only — Intuit long-polls, so don't block on it
  await pg.waitForLoadState('domcontentloaded',{timeout:8000}).catch(()=>{});
  let stable=0,lastLen=-1;
  while(Date.now()-start<timeout){
    let url=pg.url(), txt='';
    try{txt=await pg.evaluate(()=>document.body?document.body.innerText:'');}catch(e){}
    const loadingUrl=/mfdloading|\/loading/i.test(url);
    const len=txt.replace(/\s+/g,'').length;
    const painted=len>60;
    // require the painted content to hold steady for two polls (page done re-rendering)
    if(!loadingUrl && painted){ if(len===lastLen){stable++; if(stable>=1) return txt;} else {stable=0;} }
    lastLen=len;
    await sleep(700);
  }
  log('settle TIMEOUT @ '+pg.url().slice(0,80));
  try{return await pg.evaluate(()=>document.body?document.body.innerText:'');}catch(e){return '';}
}

// typeInto(): fill a field and VERIFY the value actually landed; retry up to 3x.
// Never logs the value — only its length — so secrets stay out of the log.
async function typeInto(pg,locators,value,name){
  for(let attempt=1;attempt<=3;attempt++){
    for(const loc of locators){
      try{
        const el=loc.first();
        if(!(await el.count())) continue;
        await el.click({timeout:4000}).catch(()=>{});
        await el.fill('',{timeout:4000}).catch(()=>{});
        await el.fill(value,{timeout:6000});
        const got=await el.inputValue().catch(()=>'');
        if(got.length===value.length){ log(name+' filled ok (len '+got.length+')'); return true; }
        log(name+' fill mismatch (got len '+got.length+', want '+value.length+') attempt '+attempt);
      }catch(e){ log(name+' fill err '+String(e).slice(0,50)); }
    }
    await sleep(1200);
  }
  return false;
}
const shot=async(pg,label)=>{ n++; const f=`seq-${String(n).padStart(2,'0')}-${label}.png`;
  await settle(pg); await pg.screenshot({path:f}).catch(()=>{}); log('shot '+f+' @ '+pg.url().slice(0,80)); };

(async()=>{
  const b=await chromium.launch({headless:true,args:['--no-sandbox']});
  const ctx=await b.newContext({userAgent:'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',viewport:{width:1280,height:1400}});
  const pg=await ctx.newPage();
  await pg.goto('https://accounts.intuit.com/app/sign-in?app_group=QBO&asset_alias=Intuit.accounting.core.qbowebapp',{waitUntil:'domcontentloaded',timeout:60000}).catch(()=>{});
  await shot(pg,'signin-email');
  // email — fill + verify
  await typeInto(pg,[pg.getByRole('textbox'),pg.locator('input[type=email]'),pg.locator('input')],process.env.INTUIT_EMAIL,'email');
  await shot(pg,'email-filled');
  let eb=pg.getByRole('button',{name:/sign in|continue/i}).first(); if(await eb.count())await eb.click(); else await pg.keyboard.press('Enter');
  await shot(pg,'password-page');
  // password — fill + VERIFY it landed before clicking Continue
  const pwOk=await typeInto(pg,[pg.locator('input[type=password]'),pg.getByLabel('Password'),pg.getByRole('textbox')],process.env.INTUIT_PASS,'password');
  if(!pwOk){ log('PASSWORD FILL FAILED — aborting before submit'); await shot(pg,'password-fill-failed'); await b.close(); process.exit(2); }
  let cb=pg.getByRole('button',{name:/continue|sign in/i}).first(); if(await cb.count())await cb.click(); else await pg.keyboard.press('Enter');
  await shot(pg,'after-password');
  let body=(await settle(pg)).toLowerCase();
  if(body.includes("verify it's you")||body.includes('verify your')||body.includes('a code')){
    const emailOpt=pg.getByText(/email a code/i).first();
    if(await emailOpt.count()){ await emailOpt.click(); log('chose EMAIL code'); }
    else { const t=pg.getByRole('button',{name:/text a code/i}).first(); if(await t.count()){await t.click(); log('chose TEXT code (needs John)');} }
    await shot(pg,'verify-code-entry');
    log('NEED_CODE'); let code=null;
    for(let i=0;i<300;i++){if(fs.existsSync('/tmp/intuit-code.txt')){code=fs.readFileSync('/tmp/intuit-code.txt','utf8').trim();if(code)break;}await sleep(1500);}
    if(code){
      for(const loc of [pg.getByRole('textbox'),pg.locator('input[autocomplete="one-time-code"]'),pg.locator('input[type=tel]')]){try{if(await loc.count()){await loc.first().fill(code,{timeout:5000});break;}}catch(e){}}
      let vb=pg.getByRole('button',{name:/continue|verify|sign in/i}).first(); if(await vb.count())await vb.click(); else await pg.keyboard.press('Enter');
      try{fs.unlinkSync('/tmp/intuit-code.txt');}catch(e){}
      await shot(pg,'after-code');
    } else { log('FAIL no code'); }
  }
  // skip interstitials, land — settle between each, screenshot only rendered pages
  for(let i=0;i<8;i++){
    body=(await settle(pg)).toLowerCase();
    if(body.includes('skip for now')){try{await pg.getByText(/skip for now/i).first().click({timeout:3000});await shot(pg,'skipped');continue;}catch(e){}}
    if(body.includes('remind me later')){try{await pg.getByText(/remind me later/i).first().click({timeout:3000});continue;}catch(e){}}
    break;
  }
  await shot(pg,'landed');
  await ctx.storageState({path:'.intuit-session.json'});
  log('FINAL URL: '+pg.url().slice(0,120));
  await b.close();
})();

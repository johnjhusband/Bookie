// Intuit Developer login with real MFA handling. Creds from env (never stored).
// Flow: email -> password -> "Verify it's you" (click Text a code) -> enter
// the texted code (read from /tmp/intuit-code.txt that John provides) ->
// save session -> land on developer dashboard. Confirms each screen before acting.
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
const EMAIL=process.env.INTUIT_EMAIL, PASS=process.env.INTUIT_PASS;
const SESSION=path.join(__dirname,'.intuit-session.json');
const CODE_FILE='/tmp/intuit-code.txt';
const DASH='https://developer.intuit.com/app/developer/dashboard';
const log=m=>console.log(`[intuit] ${m}`);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  if(!EMAIL||!PASS){log('FAIL: creds env missing');process.exit(2);}
  const b=await chromium.launch({headless:true,args:['--no-sandbox']});
  const ctx=await b.newContext({userAgent:'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',viewport:{width:1280,height:1400}});
  const pg=await ctx.newPage();
  await pg.goto('https://accounts.intuit.com/app/sign-in?app_group=Developer&asset_alias=Intuit.devx.devx',{waitUntil:'domcontentloaded',timeout:60000});
  await sleep(3000);
  await pg.getByRole('textbox').first().fill(EMAIL);
  let eb=pg.getByRole('button',{name:/sign in|continue/i}).first();
  if(await eb.count())await eb.click(); else await pg.keyboard.press('Enter');
  await sleep(4000);
  // password
  let filled=false;
  for(const loc of [pg.getByLabel('Password'),pg.locator('input[type="password"]'),pg.getByRole('textbox')]){
    try{if(await loc.count()){await loc.first().fill(PASS,{timeout:8000});filled=true;break;}}catch(e){}
  }
  log('password filled: '+filled);
  let cb=pg.getByRole('button',{name:/continue|sign in/i}).first();
  if(await cb.count())await cb.click(); else await pg.keyboard.press('Enter');
  await sleep(7000);
  // Verify it's you?
  let body=(await pg.evaluate(()=>document.body.innerText)).toLowerCase();
  if(body.includes("verify it's you")||body.includes('choose how you want to verify')){
    log('MFA chooser present; clicking "Text a code"');
    const textBtn=pg.getByRole('button',{name:/text a code/i}).first();
    if(await textBtn.count()){await textBtn.click();} else {log('FAIL: no Text-a-code button');await b.close();process.exit(4);}
    await sleep(5000);
    // CONFIRM a code-entry screen appeared before declaring it sent
    body=(await pg.evaluate(()=>document.body.innerText)).toLowerCase();
    const headings=await pg.evaluate(()=>Array.from(document.querySelectorAll('h1,h2,h3')).map(h=>h.innerText.trim()));
    log('after clicking Text a code, headings: '+JSON.stringify(headings));
    await pg.screenshot({path:'mfa-screen.png'}).catch(()=>{});
    if(!(body.includes('code')&&(body.includes('enter')||body.includes('sent')||body.includes('texted')))){
      log('WARN: not clearly a code-entry screen; see mfa-screen.png');
    } else {
      log('CONFIRMED: code-entry screen shown — a text was sent to the phone ending 83');
    }
    log('NEED_CODE: write the 6-digit code to /tmp/intuit-code.txt');
    try{fs.unlinkSync(CODE_FILE);}catch(e){}
    let code=null;
    for(let i=0;i<400;i++){if(fs.existsSync(CODE_FILE)){code=fs.readFileSync(CODE_FILE,'utf8').trim();if(code)break;}await sleep(1500);}
    if(!code){log('FAIL: no code provided in ~10min');await b.close();process.exit(3);}
    log('entering code');
    let entered=false;
    for(const loc of [pg.getByRole('textbox'),pg.locator('input[autocomplete="one-time-code"]'),pg.locator('input[type="tel"]')]){
      try{if(await loc.count()){await loc.first().fill(code,{timeout:6000});entered=true;break;}}catch(e){}
    }
    if(!entered){await pg.keyboard.type(code);}
    let vb=pg.getByRole('button',{name:/continue|verify|submit|sign in/i}).first();
    if(await vb.count())await vb.click(); else await pg.keyboard.press('Enter');
    await sleep(7000);
    try{fs.unlinkSync(CODE_FILE);}catch(e){}
    // possible "remember this device" prompt — accept to persist session
    const remember=pg.getByRole('button',{name:/yes|remember|continue/i}).first();
    if(await remember.count()){await remember.click().catch(()=>{});await sleep(4000);}
  } else {
    log('no MFA chooser detected; body head: '+body.slice(0,120));
  }
  // land on dashboard + save session
  if(!/developer\.intuit\.com/i.test(pg.url())){await pg.goto(DASH,{waitUntil:'domcontentloaded',timeout:60000}).catch(()=>{});await sleep(5000);}
  await ctx.storageState({path:SESSION});fs.chmodSync(SESSION,0o600);
  await pg.screenshot({path:'dashboard.png',fullPage:true}).catch(()=>{});
  log('FINAL URL: '+pg.url().slice(0,160));
  log('FINAL TITLE: '+(((await pg.title())||'').slice(0,100)));
  const signedIn=!/sign-in|login/i.test(pg.url());
  log(signedIn?'SIGNED IN — session saved':'NOT signed in — check dashboard.png');
  await b.close();
})();

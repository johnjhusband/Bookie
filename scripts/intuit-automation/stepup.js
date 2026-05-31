const { chromium } = require('playwright');
const fs=require('fs'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const log=m=>console.log('[stepup] '+m);
(async()=>{
  const b=await chromium.launch({headless:true,args:['--no-sandbox']});
  const ctx=await b.newContext({storageState:'.intuit-session.json',userAgent:'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',viewport:{width:1400,height:1700}});
  const pg=await ctx.newPage();
  await pg.goto('https://accounts.intuit.com/app/account-manager/products-billing',{waitUntil:'domcontentloaded',timeout:60000}).catch(()=>{});
  for(let i=0;i<14;i++){await sleep(2500); if(!/mfdloading/i.test(pg.url()))break;}
  await sleep(3000);
  let body=(await pg.evaluate(()=>document.body.innerText)).toLowerCase();
  if(body.includes("verify it's you")){
    const eb=pg.getByText(/email a code/i).first();
    if(await eb.count()){await eb.click();log('clicked Email a code');await sleep(5000);}
    else {log('FAIL no email option');await b.close();return;}
    log('NEED_CODE'); let code=null;
    for(let i=0;i<240;i++){if(fs.existsSync('/tmp/intuit-code.txt')){code=fs.readFileSync('/tmp/intuit-code.txt','utf8').trim();if(code)break;}await sleep(1500);}
    if(!code){log('FAIL no code');await b.close();return;}
    for(const loc of [pg.getByRole('textbox'),pg.locator('input[autocomplete="one-time-code"]'),pg.locator('input[type=tel]')]){try{if(await loc.count()){await loc.first().fill(code,{timeout:5000});break;}}catch(e){}}
    const cb=pg.getByRole('button',{name:/continue|verify|submit/i}).first(); if(await cb.count())await cb.click(); else await pg.keyboard.press('Enter');
    await sleep(7000); try{fs.unlinkSync('/tmp/intuit-code.txt');}catch(e){}
  }
  await sleep(3000);
  console.log('URL:',pg.url().slice(0,140));
  const txt=await pg.evaluate(()=>document.body.innerText.replace(/\n{2,}/g,'\n').slice(0,1200));
  console.log('--- PAGE ---'); console.log(txt);
  const links=await pg.evaluate(()=>Array.from(document.querySelectorAll('a')).map(a=>a.href).filter(h=>/qbo|realm|launch|c\d{6,}/i.test(h)));
  console.log('LINKS:',JSON.stringify([...new Set(links)].slice(0,10)));
  await pg.screenshot({path:'products-billing.png',fullPage:true}).catch(()=>{});
  await ctx.storageState({path:'.intuit-session.json'});
  await b.close();
})();

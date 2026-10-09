const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH});const page=await browser.newPage();const results=[];
 await page.route('**/backend/**',r=>r.fulfill({json:{ok:false,error:'FIXTURE: error extenso '+ 'conexión no ejecutada '.repeat(30)}}));
 await page.route(/^https?:\/\/(?!127\.0\.0\.1)/,r=>r.abort());
 for(const route of ['index','hfc','intermitencias','agotamiento-ip','puertos-docsis','recursos-zte','cmts-inits','autofind-hw','onts','troncales-pon','configuracion']){
  await page.goto(`http://127.0.0.1:8765/frontend/${route}.php`);
  for(const [width,height] of [[1920,1080],[1280,600],[390,844]]){
   await page.setViewportSize({width,height});
   for(const count of [0,1,3,20,160]){
    const g=await page.evaluate(count=>{
     const tables=[...document.querySelectorAll('table')].filter(t=>!t.closest('.hfc-modal,.ftth-modal,.temperature-detail-modal'));
     tables.forEach(t=>{t.parentElement.hidden=false;t.querySelector('tbody').innerHTML=Array.from({length:count},()=>'<tr>'+Array.from(t.querySelectorAll('th'),()=>'<td>FIXTURE: equipo / INC / WO / TAS</td>').join('')+'</tr>').join('');});
     return {overflow:document.documentElement.scrollWidth>innerWidth+1,tables:tables.map(t=>({height:t.parentElement.clientHeight,head:t.querySelector('thead').clientHeight}))};
    },count);
    assert(!g.overflow,route+' state overflow');if(count)g.tables.forEach(t=>assert(t.height>t.head,route+' row clipped'));
    results.push({route,width,height,count,...g});
   }
  }
 }
 await page.goto('http://127.0.0.1:8765/frontend/index.php');await page.setViewportSize({width:1280,height:600});
 const region=page.locator('#gkp-table-region');
 await region.evaluate(r=>{r.hidden=false;r.style.height='240px';r.querySelector('tbody').innerHTML='<tr><td>FIXTURE</td></tr>'.repeat(40);r.scrollIntoView();});
 await region.focus();await page.keyboard.press('ArrowDown');await page.waitForFunction(()=>document.querySelector('#gkp-table-region').scrollTop>0);
 const sticky=await region.evaluate(r=>Math.abs(r.querySelector('th').getBoundingClientRect().top-r.getBoundingClientRect().top));assert(sticky<2,'sticky header');
 fs.mkdirSync('artifacts/responsive',{recursive:true});fs.writeFileSync('artifacts/responsive/states.json',JSON.stringify({cases:results,keyboard:'passed',sticky:'passed'},null,2));
 await browser.close();console.log(`${results.length} state cases; keyboard and sticky passed`);
})().catch(e=>{console.error(e);process.exit(1)});

// Isolated layout fixtures: all operational APIs are blocked.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const out = process.env.RKP_VISUAL_OUTPUT || 'artifacts/responsive';
const sizes = [[2560,1440],[1920,1080],[1600,900],[1440,900],[1366,768],[1366,680],[1352,668],[1280,720],[1280,600],[1181,768],[1180,768],[1152,648],[1093,614],[1025,768],[1024,768],[1023,768],[1024,600],[820,1180],[861,600],[860,600],[768,1024],[768,600],[844,390],[683,384],[641,600],[640,600],[430,932],[390,844],[375,667],[360,800],[320,568]];
const routes = ['index','hfc','intermitencias','agotamiento-ip','puertos-docsis','recursos-zte','cmts-inits','autofind-hw','onts','troncales-pon','configuracion'];
(async () => {
 fs.mkdirSync(out,{recursive:true});
 const browser = await chromium.launch({executablePath:process.env.CHROMIUM_PATH});
 const page = await browser.newPage(); const report=[];
 await page.route('**/backend/**', route => route.fulfill({json:{ok:false,error:'Fixture aislada: consulta no ejecutada'}}));
 await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, route=>route.abort());
 for(const route of process.env.WHEEL_ONLY ? [] : routes){
  console.log('Checking '+route);
  await page.goto(`http://127.0.0.1:8765/frontend/${route}.php`);
  await page.waitForTimeout(250);
  await page.evaluate(()=>{
   document.querySelectorAll('table').forEach(t=>{
    if(t.closest('[hidden], .hfc-modal, .ftth-modal, .temperature-detail-modal')) return;
    t.parentElement.hidden=false;
    t.querySelector('tbody').innerHTML=Array.from({length:160},()=>'<tr>'+Array.from(t.querySelectorAll('th'),(_,i)=>`<td>${i===0?'FIXTURE-EQUIPO-LARGO-'.repeat(4):'INC123 / WO456 / TAS789'}</td>`).join('')+'</tr>').join('');
   });
  });
  for(const [width,height] of sizes){
   await page.setViewportSize({width,height});
   for(const collapsed of width>=1024?[false,true]:[false]){
    await page.evaluate(v=>document.body.classList.toggle('sidebar-collapsed',v),collapsed);
    await page.waitForTimeout(230);
    const g=await page.evaluate(()=>{
     const f=document.querySelector('.footer'),content=document.querySelector('.gkp-content,.module-content');
     return {scroll:document.documentElement.scrollWidth,footer:f.getBoundingClientRect().top,contentBottom:content.getBoundingClientRect().bottom,tables:[...document.querySelectorAll('table')].filter(t=>t.getBoundingClientRect().height>0).map(t=>({height:t.parentElement.clientHeight,head:t.querySelector('thead').getBoundingClientRect().height}))};
    });
    assert(g.scroll<=width+1,`${route} ${width}: overflow ${g.scroll}`);
    assert(g.footer>=g.contentBottom-1,`${route}: footer overlap`);
    g.tables.forEach(t=>assert(t.height>t.head+20,`${route}: collapsed rows`));
    report.push({route,width,height,collapsed,...g});
   }
   if(route==='index'&&[[1920,1080],[1366,680],[1280,600],[390,844]].some(s=>s[0]===width&&s[1]===height)){
    await page.evaluate(()=>{document.body.classList.remove('sidebar-collapsed');window.scrollTo(0,0)});
    await page.waitForTimeout(250);
    await page.screenshot({path:`${out}/index-${width}-${height}.png`,fullPage:true});
   }
  }
 }
 await page.goto('http://127.0.0.1:8765/frontend/index.php'); await page.setViewportSize({width:1280,height:600});
 await page.evaluate(()=>{
  const spacer=document.createElement('div');spacer.style.height='1000px';spacer.textContent='FIXTURE: continuación de página';document.querySelector('.gkp-content').append(spacer);
  const r=document.querySelector('#gkp-table-region');r.hidden=false;r.querySelector('tbody').innerHTML=Array.from({length:20},()=>'<tr>'+Array.from({length:6},()=>'<td>FIXTURE '+ 'texto '.repeat(8)+'</td>').join('')+'</tr>').join('');
  r.style.height='240px';r.querySelector('table').style.minWidth='2000px';r.scrollIntoView();
 });
 const region=page.locator('#gkp-table-region');
 const hover=async()=>{const b=await region.boundingBox();await page.mouse.move(b.x+50,Math.min(b.y+80,550));};
 const pos=()=>region.evaluate(r=>({x:r.scrollLeft,y:r.scrollTop,page:window.scrollY}));
 await hover();let before=await pos();await page.mouse.wheel(0,100);await page.waitForTimeout(180);let after=await pos();assert(after.y>before.y&&after.page===before.page,'vertical native wheel');
 await page.keyboard.down('Shift');await page.mouse.wheel(0,100);await page.keyboard.up('Shift');await page.waitForTimeout(180);assert((await pos()).x>after.x,'shift wheel');
 before=await pos();await page.mouse.wheel(100,0);await page.waitForTimeout(180);assert((await pos()).x>before.x,'touchpad horizontal');
 await region.evaluate(r=>r.scrollTop=r.scrollHeight);await hover();before=await pos();await page.mouse.wheel(0,150);await page.waitForTimeout(180);assert((await pos()).page>before.page,'vertical edge chains to page');
 await region.evaluate(r=>{r.querySelector('tbody').innerHTML=r.querySelector('tbody tr').outerHTML;r.scrollLeft=0;r.scrollIntoView();});await hover();await page.mouse.wheel(0,100);await page.waitForTimeout(180);assert((await pos()).x>0,'horizontal only normal wheel');
 await region.evaluate(r=>{r.scrollLeft=r.scrollWidth;r.scrollIntoView();});await page.waitForTimeout(800);await hover();before=await pos();await page.mouse.wheel(0,150);await page.waitForTimeout(180);assert((await pos()).page>before.page,'horizontal edge chains '+JSON.stringify({before,after:await pos(),geometry:await region.evaluate(r=>({h:r.scrollHeight,ch:r.clientHeight,w:r.scrollWidth,cw:r.clientWidth,rect:r.getBoundingClientRect().toJSON(),doc:document.documentElement.scrollHeight}))}));
 await region.evaluate(r=>{r.querySelector('table').style.minWidth='0';r.querySelector('tbody').innerHTML='<tr><td>Fixture</td></tr>';r.scrollIntoView();});await hover();before=await pos();await page.mouse.wheel(0,100);await page.waitForTimeout(180);assert((await pos()).page>before.page,'no overflow chains');
 const ctrl=await region.evaluate(r=>{const e=new WheelEvent('wheel',{deltaY:100,ctrlKey:true,bubbles:true,cancelable:true});r.dispatchEvent(e);return e.defaultPrevented;});assert(!ctrl,'ctrl untouched');
 await page.setViewportSize({width:390,height:844});await page.evaluate(()=>window.scrollTo(0,0));await page.locator('#sidebar-toggle').click();assert(await page.locator('body').evaluate(e=>e.classList.contains('sidebar-open')));await page.keyboard.press('Escape');assert(await page.locator('#sidebar-toggle').evaluate(e=>document.activeElement===e));
 await page.setViewportSize({width:1280,height:600});await page.evaluate(()=>{const m=document.querySelector('#ftth-modal');m.hidden=false;m.querySelector('.ftth-dialog__body').insertAdjacentHTML('beforeend','<p>FIXTURE modal '+ 'Lista larga '.repeat(500)+'</p>');});await page.screenshot({path:`${out}/modal-1280-600.png`,fullPage:true});
 fs.writeFileSync(`${out}/results.json`,JSON.stringify({browser:process.env.CHROMIUM_PATH,cases:report,wheel:'passed',drawer:'passed',zoom:'not executed'},null,2));
 await browser.close();console.log(`${report.length} geometry cases; wheel and drawer passed`);
})().catch(e=>{console.error(e);process.exit(1)});

/* Visual fixtures only: never writes collector CSVs or reaches private APIs.
   PLAYWRIGHT_MODULE points to an installed playwright package.
   CHROMIUM_PATH optionally selects an installed Chromium executable.
   RKP_VISUAL_URL defaults to the local PHP server. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.RKP_VISUAL_URL || 'http://127.0.0.1:8765';
const out = process.env.RKP_VISUAL_OUTPUT || '.';
const rows = Array.from({length:160}, (_,i) => ({cmts:`CMTS-${String(i).padStart(3,'0')}-${'Nombre largo '.repeat(3)}`,ip:`10.0.0.${i}`,fecha:'2026-10-09T15:30:00Z',total_init:i===1?null:i===0?122:0,ok:i!==1,estado:i===1?'ERROR DE CONSULTA':i===0?'CRITICO':'SIN INIT',variacion:i===1?null:12,comparado_con:'2026-10-09T14:30:00Z',error:i===1?'Timeout SSH: '+ 'Error real con contexto de conexión. '.repeat(25):''}));
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage(); const requests=[]; let active=false;
 await page.route('**/backend/**', async route=>{
  const req=route.request(),url=new URL(req.url()),action=url.searchParams.get('accion'); requests.push({action,method:req.method(),cmts:url.searchParams.get('cmts')});
  let data={};
  if(action==='actual')data={items:rows};
  if(action==='estado')data={enabled:true,active,run_id:'fixture',last_completed_at:'2026-10-09T15:30:00Z',progreso:{run_id:'fixture',total:160,completed:80}};
  if(action==='historico')data={items:rows.slice(0,100),total:160};
  if(action==='tendencia')data=rows.filter(x=>x.ok).slice(0,20);
  if(action==='actualizar'||action==='probar')active=true;
  if(action==='exportar')return route.fulfill({body:'cmts,total_init\nfixture,122',contentType:'text/csv'});
  await route.fulfill({status:action==='actualizar'||action==='probar'?202:200,json:{ok:true,data,estado:'iniciado'}});
 });
 await page.goto(`${base}/frontend/cmts-inits.php`); await page.waitForSelector('#init-rows tr');
 const report=[];
 for(const [width,height] of [[1366,768],[1920,1080],[1181,768],[1180,768],[1024,768],[768,1024],[390,844],[360,800],[1093,614],[683,384]]){
  await page.setViewportSize({width,height});
  for(const collapsed of [false,true]){
   await page.evaluate(v=>document.body.classList.toggle('sidebar-collapsed',v),collapsed); await page.waitForTimeout(600);
   const geometry=await page.evaluate(()=>{
    const e=document.querySelector('.init-table-scroll'),r=e.getBoundingClientRect(),head=e.querySelector('thead').getBoundingClientRect();
    const lower=document.querySelector('.init-history'); lower.scrollIntoView(); const visible=lower.getBoundingClientRect(); window.scrollTo(0,0);
    return {width:innerWidth,scroll:document.documentElement.scrollWidth,tableHeight:r.height,headerHeight:head.height,tableTop:r.top,tableWidth:e.scrollWidth,clientWidth:e.clientWidth,historyReachable:visible.top<innerHeight&&visible.bottom>0,canvasWidth:document.querySelector('canvas').width,ancestors:['.app','.main','.module-content','.init-table-panel','.init-table-scroll'].map(sel=>{const el=document.querySelector(sel),s=getComputedStyle(el);return {sel,height:el.getBoundingClientRect().height,overflow:s.overflow,shrink:s.flexShrink,minWidth:s.minWidth,minHeight:s.minHeight};})};
   });
   assert(geometry.scroll<=width,JSON.stringify(geometry)); assert(geometry.tableHeight>geometry.headerHeight+100); assert(geometry.historyReachable);
   if(width===1366)assert(geometry.tableTop+geometry.headerHeight+47<height);
   report.push({width,height,collapsed,...geometry});
  }
  if(width===1366||width===390){ await page.evaluate(()=>document.body.classList.remove('sidebar-collapsed')); await page.waitForTimeout(600); await page.screenshot({path:`${out}/init-${width}.png`,fullPage:true}); }
 }
 await page.setViewportSize({width:1366,height:768});
 await page.locator('[data-sort="cmts"]').click(); assert.equal(await page.locator('[data-sort="cmts"]').evaluate(e=>e.parentElement.getAttribute('aria-sort')),'ascending');
 await page.locator('#init-search').fill('NO MATCH'); assert.match(await page.locator('#init-empty').innerText(),/Sin coincidencias/);
 await page.locator('#init-search').fill(''); await page.locator('#init-filter').selectOption('error'); assert.equal(await page.locator('#init-rows tr').count(),1);
 const summary=page.locator('.init-error summary'); await summary.focus(); await page.keyboard.press('Enter'); assert(await page.locator('.init-error').evaluate(e=>e.open)); assert.match(await page.locator('.init-error p').innerText(),/Timeout SSH/); await page.keyboard.press('Enter'); assert(!(await page.locator('.init-error').evaluate(e=>e.open)));
 await page.locator('.init-probe').click(); await page.waitForTimeout(100); assert(requests.some(x=>x.action==='probar'&&x.method==='POST'&&x.cmts===rows[1].cmts));
 await page.locator('#init-refresh').click(); await page.waitForTimeout(100); assert(requests.some(x=>x.action==='actualizar'&&x.method==='POST'));
 const download=page.waitForEvent('download'); await page.locator('#init-export').click(); await download;
 const tables=[];
 for(const path of ['index.php','hfc.php','intermitencias.php','agotamiento-ip.php','puertos-docsis.php','recursos-zte.php']){
  await page.goto(`${base}/frontend/${path}`);
  await page.evaluate(()=>document.querySelectorAll('table').forEach(table=>{const wrap=table.parentElement;wrap.hidden=false;table.querySelector('tbody').innerHTML=Array.from({length:20},()=>'<tr>'+Array.from(table.querySelectorAll('th'),(_,i)=>`<td>${i===0?'EQUIPO-'.repeat(15):'123 · dato operacional'}</td>`).join('')+'</tr>').join('');}));
  for(const width of [1366,1181,1180,390,360]){
   await page.setViewportSize({width,height:768}); await page.waitForTimeout(600);
   const measurement=await page.evaluate(()=>({page:document.documentElement.scrollWidth,width:innerWidth,tables:[...document.querySelectorAll('table')].map(t=>({wrapper:t.parentElement.className,client:t.parentElement.clientWidth,scroll:t.parentElement.scrollWidth,height:t.parentElement.clientHeight,overflow:getComputedStyle(t.parentElement).overflow,sticky:getComputedStyle(t.querySelector('th')).position}))}));
   assert(measurement.page<=width,JSON.stringify({path,...measurement})); tables.push({path,...measurement});
  }
 }
 fs.writeFileSync(`${out}/geometry.json`,JSON.stringify({init:report,tables,requests},null,2));
 await browser.close(); console.log(JSON.stringify({initCases:report.length,otherTableCases:tables.length,functional:'passed',overflow:tables.filter(x=>x.page>x.width)},null,2));
})().catch(e=>{console.error(e);process.exit(1)});

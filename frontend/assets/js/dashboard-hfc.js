window.hfcSourceAge=iso=>{
  const d=new Date(iso);if(!Number.isFinite(d.getTime()))return 'Sin información';
  const minutes=Math.max(0,Math.floor((Date.now()-d.getTime())/60000));
  const age=minutes>=1440?`${Math.floor(minutes/1440)} días`:minutes>=60?`${Math.floor(minutes/60)} h`:`${minutes} min`;
  return `${d.toLocaleString('es-CO',{timeZone:'America/Bogota',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:false})} · hace ${age}`;
};
/* Shared metadata fetch: one in-flight request and short-lived response. */
(() => {
  const nativeFetch=window.fetch.bind(window), cache=new Map();
  window.fetch=function(input,options){
    const url=typeof input==='string'?input:'';
    if(!/[?&]action=(actualizaciones|qoe_actualizacion)(?:&|$)/.test(url))return nativeFetch(input,options);
    const now=Date.now(),old=cache.get(url);
    if(old && old.expires>now)return old.promise.then(r=>r.clone());
    const promise=nativeFetch(input,options);
    cache.set(url,{promise,expires:now+10000});
    promise.catch(()=>cache.delete(url));
    return promise.then(r=>r.clone());
  };
})();

const HFC_PRIORITY_CAPITALS={
  "VALLE":"CALI",
  "RISARALDA":"PEREIRA",
  "QUINDIO":"ARMENIA",
  "CAUCA":"POPAYAN",
  "CALDAS":"MANIZALES"
};
(()=>{"use strict";
const app=document.getElementById("hfcApp");if(!app)return;
const API={estado:app.dataset.apiEstado,inc:app.dataset.apiInc,base:app.dataset.apiBase,incImport:app.dataset.apiIncImport};
const $=id=>document.getElementById(id),fmt=n=>new Intl.NumberFormat("es-CO").format(Number(n||0)),esc=s=>String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
const PAGE=35;let rows=[],incs=[],filtered=[],page=1,selectedZone="";

/* CATALOGO NODOS COMUNIDAD ALIADO JS V1 */
let selectedZones=new Set();

/* BEGIN HFC MULTIFILTRO ESTADO INCIDENTE V1 */
let selectedStates=new Set();
let selectedIncStatuses=new Set();

function hfcMultiFilterOptions(selectId){
  const select=$(selectId);
  if(!select)return [];
  return [...select.options]
    .filter(o=>String(o.value||"").trim()!=="")
    .map(o=>({
      value:String(o.value),
      label:String(o.textContent||o.value)
    }));
}

function hfcMultiFilterText(textId,selectedSet,emptyText,singular,plural){
  const el=$(textId);
  if(!el)return;

  if(selectedSet.size===0){
    el.textContent=emptyText;
  }else if(selectedSet.size===1){
    el.textContent=[...selectedSet][0];
  }else{
    el.textContent=`${selectedSet.size} ${plural}`;
  }
}

function stateMultiEnsure(){
  const select=$("fState");
  if(!select || document.getElementById("stateMulti"))return;

  select.style.display="none";

  const wrap=document.createElement("div");
  wrap.className="hfc-filter-multi";
  wrap.id="stateMulti";

  wrap.innerHTML=`
    <button type="button"
            class="hfc-filter-multi-trigger"
            id="stateMultiTrigger"
            aria-haspopup="true"
            aria-expanded="false">
      <span id="stateMultiText">Todos</span>
      <i class="fas fa-chevron-down"></i>
    </button>

    <div class="hfc-filter-multi-menu" id="stateMultiMenu">
      <div class="hfc-filter-multi-actions">
        <button type="button" id="stateSelectAll">Seleccionar todos</button>
        <button type="button" id="stateClearAll">Limpiar</button>
      </div>

      <div class="hfc-filter-multi-options" id="stateMultiOptions"></div>
    </div>
  `;

  select.insertAdjacentElement("afterend",wrap);

  $("stateMultiTrigger").onclick=e=>{
    e.stopPropagation();

    document.querySelectorAll(".hfc-filter-multi.open").forEach(x=>{
      if(x!==wrap)x.classList.remove("open");
    });

    wrap.classList.toggle("open");
    $("stateMultiTrigger").setAttribute(
      "aria-expanded",
      wrap.classList.contains("open") ? "true" : "false"
    );
  };

  $("stateSelectAll").onclick=e=>{
    e.stopPropagation();
    selectedStates=new Set(
      hfcMultiFilterOptions("fState").map(x=>x.value)
    );
    stateMultiRender();
    apply();
  };

  $("stateClearAll").onclick=e=>{
    e.stopPropagation();
    selectedStates.clear();
    stateMultiRender();
    apply();
  };

  document.addEventListener("click",e=>{
    if(!wrap.contains(e.target)){
      wrap.classList.remove("open");
      $("stateMultiTrigger")?.setAttribute("aria-expanded","false");
    }
  });
}

function stateMultiRender(){
  stateMultiEnsure();

  const box=$("stateMultiOptions");
  if(!box)return;

  const options=hfcMultiFilterOptions("fState");
  const valid=new Set(options.map(x=>x.value));

  selectedStates=new Set(
    [...selectedStates].filter(x=>valid.has(x))
  );

  box.innerHTML=options.map(x=>`
    <label class="hfc-filter-multi-option">
      <input type="checkbox"
             value="${esc(x.value)}"
             ${selectedStates.has(x.value)?"checked":""}>
      <span>${esc(x.label)}</span>
    </label>
  `).join("");

  box.querySelectorAll('input[type="checkbox"]').forEach(ch=>{
    ch.onchange=()=>{
      if(ch.checked){
        selectedStates.add(ch.value);
      }else{
        selectedStates.delete(ch.value);
      }

      stateMultiText();
      apply();
    };
  });

  stateMultiText();
}

function stateMultiText(){
  hfcMultiFilterText(
    "stateMultiText",
    selectedStates,
    "Todos",
    "estado",
    "estados seleccionados"
  );
}

function incMultiEnsure(){
  const select=$("fInc");
  if(!select || document.getElementById("incMulti"))return;

  select.style.display="none";

  const wrap=document.createElement("div");
  wrap.className="hfc-filter-multi";
  wrap.id="incMulti";

  wrap.innerHTML=`
    <button type="button"
            class="hfc-filter-multi-trigger"
            id="incMultiTrigger"
            aria-haspopup="true"
            aria-expanded="false">
      <span id="incMultiText">Todos</span>
      <i class="fas fa-chevron-down"></i>
    </button>

    <div class="hfc-filter-multi-menu" id="incMultiMenu">
      <div class="hfc-filter-multi-actions">
        <button type="button" id="incSelectAll">Seleccionar todos</button>
        <button type="button" id="incClearAll">Limpiar</button>
      </div>

      <div class="hfc-filter-multi-options" id="incMultiOptions"></div>
    </div>
  `;

  select.insertAdjacentElement("afterend",wrap);

  $("incMultiTrigger").onclick=e=>{
    e.stopPropagation();

    document.querySelectorAll(".hfc-filter-multi.open").forEach(x=>{
      if(x!==wrap)x.classList.remove("open");
    });

    wrap.classList.toggle("open");
    $("incMultiTrigger").setAttribute(
      "aria-expanded",
      wrap.classList.contains("open") ? "true" : "false"
    );
  };

  $("incSelectAll").onclick=e=>{
    e.stopPropagation();
    selectedIncStatuses=new Set(
      hfcMultiFilterOptions("fInc").map(x=>x.value)
    );
    incMultiRender();
    apply();
  };

  $("incClearAll").onclick=e=>{
    e.stopPropagation();
    selectedIncStatuses.clear();
    incMultiRender();
    apply();
  };

  document.addEventListener("click",e=>{
    if(!wrap.contains(e.target)){
      wrap.classList.remove("open");
      $("incMultiTrigger")?.setAttribute("aria-expanded","false");
    }
  });
}

function incMultiRender(){
  incMultiEnsure();

  const box=$("incMultiOptions");
  if(!box)return;

  const options=hfcMultiFilterOptions("fInc");
  const valid=new Set(options.map(x=>x.value));

  selectedIncStatuses=new Set(
    [...selectedIncStatuses].filter(x=>valid.has(x))
  );

  box.innerHTML=options.map(x=>`
    <label class="hfc-filter-multi-option">
      <input type="checkbox"
             value="${esc(x.value)}"
             ${selectedIncStatuses.has(x.value)?"checked":""}>
      <span>${esc(x.label)}</span>
    </label>
  `).join("");

  box.querySelectorAll('input[type="checkbox"]').forEach(ch=>{
    ch.onchange=()=>{
      if(ch.checked){
        selectedIncStatuses.add(ch.value);
      }else{
        selectedIncStatuses.delete(ch.value);
      }

      incMultiText();
      apply();
    };
  });

  incMultiText();
}

function incMultiText(){
  hfcMultiFilterText(
    "incMultiText",
    selectedIncStatuses,
    "Todos",
    "opción",
    "opciones seleccionadas"
  );
}
/* END HFC MULTIFILTRO ESTADO INCIDENTE V1 */


function zoneMultiEnsure(){
  const select=$("fZone");
  if(!select || document.getElementById("zoneMulti"))return;

  select.style.display="none";

  const wrap=document.createElement("div");
  wrap.className="hfc-zone-multi";
  wrap.id="zoneMulti";
  wrap.innerHTML=`
    <button type="button" class="hfc-zone-trigger" id="zoneMultiTrigger">
      <span id="zoneMultiText">Todas</span>
      <i class="fas fa-chevron-down"></i>
    </button>
    <div class="hfc-zone-menu" id="zoneMultiMenu">
      <div class="hfc-zone-actions">
        <button type="button" id="zoneSelectAll">Todas</button>
        <button type="button" id="zoneClearAll">Limpiar</button>
      </div>
      <div class="hfc-zone-options" id="zoneMultiOptions"></div>
    </div>`;
  select.parentElement.appendChild(wrap);

  $("zoneMultiTrigger").onclick=e=>{
    e.stopPropagation();
    wrap.classList.toggle("open");
  };
  $("zoneSelectAll").onclick=()=>{
    selectedZones=new Set(rows.map(r=>r.zona).filter(Boolean));
    zoneMultiRender();
    selectedZone="";
    apply();
  };
  $("zoneClearAll").onclick=()=>{
    selectedZones.clear();
    zoneMultiRender();
    selectedZone="";
    apply();
  };
  document.addEventListener("click",e=>{
    if(!wrap.contains(e.target))wrap.classList.remove("open");
  });
}

function zoneMultiText(){
  const el=$("zoneMultiText");if(!el)return;
  if(selectedZones.size===0)el.textContent="Todas";
  else if(selectedZones.size===1)el.textContent=[...selectedZones][0];
  else el.textContent=`${selectedZones.size} zonas seleccionadas`;
}

function zoneMultiRender(){
  zoneMultiEnsure();
  const box=$("zoneMultiOptions");if(!box)return;
  const zones=[...new Set(rows.map(r=>r.zona).filter(Boolean))].sort();
  selectedZones=new Set([...selectedZones].filter(z=>zones.includes(z)));
  box.innerHTML=zones.map(z=>`
    <label class="hfc-zone-option">
      <input type="checkbox" value="${esc(z)}" ${selectedZones.has(z)?"checked":""}>
      <span>${esc(z)}</span>
    </label>`).join("");
  box.querySelectorAll('input[type="checkbox"]').forEach(ch=>{
    ch.onchange=()=>{
      ch.checked?selectedZones.add(ch.value):selectedZones.delete(ch.value);
      selectedZone="";
      zoneMultiText();
      apply();
    };
  });
  zoneMultiText();
}

const affected=r=>[
  "DESENGANCHE PARCIAL",
  "DESENGANCHE TOTAL",
  "POSIBLE DESENGANCHE TOTAL / HISTORICO",
  "POSIBLE CAIDA PROLONGADA / HISTORICO"
].includes(r.observacion);

const totalAffectedState=s=>[
  "DESENGANCHE TOTAL",
  "POSIBLE DESENGANCHE TOTAL / HISTORICO"
].includes(s);

const partialAffectedState=s=>[
  "DESENGANCHE PARCIAL",
  "POSIBLE CAIDA PROLONGADA / HISTORICO"
].includes(s);
const vendor=r=>(r.fabricante||"CASA").toUpperCase();
const incText=r=>r.inc_status==="CON INCIDENTE"?(r.incidente||"CON INCIDENTE"):r.inc_status;
function badgeState(s){let c="review";if(s==="ENGANCHADO"||s==="OPERATIVO")c="ok";else if(s==="DESENGANCHE PARCIAL"||s==="POSIBLE CAIDA PROLONGADA / HISTORICO")c="warn";else if(s==="DESENGANCHE TOTAL"||s==="POSIBLE DESENGANCHE TOTAL / HISTORICO")c="bad";return `<span class="badge ${c}">${esc(s)}</span>`}
function hfcDescripcionCorta(valor){
  const texto=String(valor||"").trim();

  if(!texto){
    return "";
  }

  const marca=" | VALIDACION HISTORICA";

  if(texto.includes(marca)){
    const base=texto.split(marca)[0].trim();

    if(base){
      return base+" | Validación histórica";
    }
  }

  if(texto.length>115){
    return texto.slice(0,112).trim()+"...";
  }

  return texto;
}

/* HFC HELIX: INC, WO y TAS por nodo */

const hfcHelixCache = new Map();
const hfcHelixPendientes = [];
const hfcHelixEnCola = new Set();
let hfcHelixProcesando = false;

const HFC_HELIX_TTL_OK = 120000;
const HFC_HELIX_TTL_ERROR = 30000;
const HFC_HELIX_PAUSA = 2000;

function hfcHelixNodo(valor) {
  return String(valor ?? "").trim().toUpperCase();
}

function hfcHelixEstado(nodo) {
  const dato = hfcHelixCache.get(nodo);
  if (!dato) return null;

  if (Date.now() - dato.fecha > (
    dato.estado === "ok"
      ? HFC_HELIX_TTL_OK
      : HFC_HELIX_TTL_ERROR
  )) {
    hfcHelixCache.delete(nodo);
    return null;
  }

  return dato;
}

function hfcHelixHTML(nodo) {
  const dato = hfcHelixEstado(nodo);

  if (!dato) {
    return '<small class="hfc-helix-status">Helix: pendiente</small>';
  }

  if (dato.estado === "error") {
    return '<small class="hfc-helix-status">Helix: no disponible</small>';
  }

  const d = dato.data;
  const inc = Number(d.inc || 0);
  const wo = Number(d.wo || 0);
  const tas = Number(d.tas || 0);

  if (inc + wo + tas === 0) {
    return '<small class="hfc-helix-status">Helix: Sin casos</small>';
  }

  return `
    <div class="hfc-helix-cases">
      <span class="badge review">INC ${inc}</span>
      <span class="badge review">WO ${wo}</span>
      <span class="badge review">TAS ${tas}</span>
    </div>
  `;
}

function badgeInc(r) {
  let c = "review";

  if (r.inc_status === "CON INCIDENTE") c = "ok";
  else if (r.inc_status === "SIN INCIDENTE") c = "bad";
  else if (r.inc_status === "NO APLICA") c = "neutral";

  const nodo = hfcHelixNodo(r.service_group);

  return `
    <div class="hfc-inc-cell">
      <span class="badge ${c}">${esc(incText(r))}</span>
      <div class="hfc-helix-result">
        ${hfcHelixHTML(nodo)}
      </div>
    </div>
  `;
}

function hfcHelixActualizarFilas(nodo) {
  document.querySelectorAll("#networkBody tr[data-node]").forEach(tr => {
    if (hfcHelixNodo(tr.dataset.node) !== nodo) return;

    const fila = window.__HFC_EXEC_CURRENT_ROWS__?.[
      Number(tr.dataset.index)
    ];

    if (!fila) return;

    const celda = tr.children[7];
    if (celda) celda.innerHTML = badgeInc(fila);
  });
}

function hfcHelixEsperar(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function hfcHelixProcesarCola() {
  if (hfcHelixProcesando) return;

  hfcHelixProcesando = true;

  try {
    while (hfcHelixPendientes.length) {
      const nodo = hfcHelixPendientes.shift();
      hfcHelixEnCola.delete(nodo);

      if (hfcHelixEstado(nodo)) {
        hfcHelixActualizarFilas(nodo);
        continue;
      }

      // Evitar consultar nodos que ya no están visibles.
      const visible = [...document.querySelectorAll(
        "#networkBody tr[data-node]"
      )].some(tr => hfcHelixNodo(tr.dataset.node) === nodo);

      if (!visible) continue;

      try {
        const url = window.dhUrl(
          "backend/api/hfc_casos_helix.php"
        );

        const respuesta = await fetch(
          url + "?nodo=" + encodeURIComponent(nodo),
          {
            method: "GET",
            headers: { Accept: "application/json" },
            signal: AbortSignal.timeout(40000)
          }
        );

        if (!respuesta.ok) {
          throw new Error("HTTP " + respuesta.status);
        }

        const json = await respuesta.json();

        if (
          json.ok !== true ||
          !json.data ||
          hfcHelixNodo(json.data.nodo) !== nodo ||
          !["inc", "wo", "tas"].every(
            campo => Number.isFinite(Number(json.data[campo]))
          )
        ) {
          throw new Error("Respuesta Helix inválida");
        }

        hfcHelixCache.set(nodo, {
          estado: "ok",
          data: json.data,
          fecha: Date.now()
        });

      } catch (error) {
        console.warn("[HFC HELIX]", nodo, error.message);

        hfcHelixCache.set(nodo, {
          estado: "error",
          fecha: Date.now()
        });
      }

      hfcHelixActualizarFilas(nodo);

      await hfcHelixEsperar(HFC_HELIX_PAUSA);
    }
  } finally {
    hfcHelixProcesando = false;
  }
}

function hfcHelixConsultarVisibles() {
  // Descartar solicitudes pendientes de páginas anteriores.
  hfcHelixPendientes.length = 0;
  hfcHelixEnCola.clear();

  document.querySelectorAll("#networkBody tr[data-node]").forEach(tr => {
    const nodo = hfcHelixNodo(tr.dataset.node);

    if (!/^[A-Z0-9._-]{1,120}$/.test(nodo)) return;
    if (hfcHelixEstado(nodo) || hfcHelixEnCola.has(nodo)) return;

    hfcHelixPendientes.push(nodo);
    hfcHelixEnCola.add(nodo);
  });

  void hfcHelixProcesarCola();
}

/* HFC TABLE HEADERS UPDATE V1 */
function hfcFormatUpdate(meta){
  if(!meta || !meta.existe || !meta.iso)return "Sin información";
  const d=new Date(meta.iso);
  if(Number.isNaN(d.getTime()))return meta.texto||"Sin información";
  return d.toLocaleString("es-CO",{
    timeZone:"America/Bogota",year:"numeric",month:"2-digit",day:"2-digit",
    hour:"2-digit",minute:"2-digit",second:"2-digit",
    hour12:false
  });
}

function ensureHfcTableHeaders(){
  const networkBody=$("networkBody");
  const networkWrap=networkBody?.closest(".hfc-table-wrap");
  if(networkWrap && !document.getElementById("hfcNetworkTableHead")){
    const head=document.createElement("div");
    head.className="hfc-table-section-head";
    head.id="hfcNetworkTableHead";
    head.innerHTML=`
      <div class="hfc-table-section-title">
        <strong>Estado de red</strong>
        <span>Última actualización: <b id="estadoRedUpdatedAt">Consultando...</b></span>
      </div>
      <div class="hfc-table-section-actions" id="hfcNetworkActions"></div>`;
    networkWrap.parentElement.insertBefore(head,networkWrap);

    const btn=$("btnExportVista");
    const actions=$("hfcNetworkActions");
    if(btn && actions){
      actions.appendChild(btn);
      btn.classList.add("hfc-table-download");
    }
  }

  const incBody=$("incBody");
  const incWrap=incBody?.closest(".hfc-table-wrap");
  if(incWrap && !document.getElementById("hfcNetcoolTableHead")){
    const head=document.createElement("div");
    head.className="hfc-table-section-head hfc-table-section-head-netcool";
    head.id="hfcNetcoolTableHead";
    head.innerHTML=`
      <div class="hfc-table-section-title">
        <strong>Incidentes NETCOOL</strong>
        <span>Última actualización: <b id="netcoolUpdatedAt">Consultando...</b></span>
      </div>`;
    incWrap.parentElement.insertBefore(head,incWrap);
  }
}

async function refreshHfcUpdateTimes(){
  ensureHfcTableHeaders();
  try{
    const r=await fetch(window.dhUrl("api/dashboard_hfc/actualizaciones.php", "frontend"),{
      cache:"no-store",
      headers:{"Accept":"application/json"}
    });
    const j=await r.json();
    if(!r.ok || j.ok===false)throw new Error(j.error||`HTTP ${r.status}`);

    const e=$("estadoRedUpdatedAt");
    const n=$("netcoolUpdatedAt");
    if(e)e.textContent=hfcFormatUpdate(j.estado_red);
    if(n)n.textContent=hfcFormatUpdate(j.netcool);
  }catch(err){
    const e=$("estadoRedUpdatedAt");
    const n=$("netcoolUpdatedAt");
    if(e)e.textContent="No disponible";
    if(n)n.textContent="No disponible";
    console.warn("No fue posible consultar fechas HFC:",err);
  }
}
/* HFC AUTO SOURCE HEADER V1 */
function hfcAutoAgeClass(meta,kind){
  if(!meta || !meta.iso)return "hfc-source-bad";
  const ts=new Date(meta.iso).getTime();
  if(!Number.isFinite(ts))return "hfc-source-bad";
  const mins=Math.max(0,(Date.now()-ts)/60000);

  if(kind==="cmts"){
    if(mins<=45)return "hfc-source-ok";
    if(mins<=90)return "hfc-source-warn";
    return "hfc-source-bad";
  }

  if(mins<=1440)return "hfc-source-ok";
  if(mins<=2880)return "hfc-source-warn";
  return "hfc-source-bad";
}

function ensureHfcAutoSourceHeader(){
  const app=document.getElementById("hfcApp");
  if(!app)return;

  /* Retirar la tarjeta separada antigua si existe. */
  const old=document.getElementById("hfcAutoSourceHeader");
  if(old && old.parentElement)old.remove();

  const hero=app.querySelector(".hfc-hero");
  if(!hero)return;

  let meta=document.getElementById("hfcExecMeta");
  if(meta)return;

  meta=document.createElement("div");
  meta.id="hfcExecMeta";
  meta.className="hfc-exec-meta";
  meta.innerHTML=`
    <div class="hfc-exec-source" id="hfcAutoCmtsCard">
      <span class="hfc-auto-source-dot"></span>
      <span class="hfc-exec-source-label">CMTS / HFC</span>
      <strong id="hfcAutoCmtsTime">Consultando...</strong>
    </div>
    <div class="hfc-exec-source" id="hfcAutoNetcoolCard">
      <span class="hfc-auto-source-dot"></span>
      <span class="hfc-exec-source-label">NETCOOL</span>
      <strong id="hfcAutoNetcoolTime">Consultando...</strong>
    </div>`;

  const refreshBtn=hero.querySelector("button");
  if(refreshBtn && refreshBtn.parentElement){
    refreshBtn.parentElement.insertBefore(meta,refreshBtn);
  }else{
    hero.appendChild(meta);
  }
}
async function refreshHfcAutoSourceHeader(){
  ensureHfcAutoSourceHeader();

  const cmtsCard=document.getElementById("hfcAutoCmtsCard");
  const netCard=document.getElementById("hfcAutoNetcoolCard");
  const cmtsTime=document.getElementById("hfcAutoCmtsTime");
  const netTime=document.getElementById("hfcAutoNetcoolTime");

  try{
    const r=await fetch(window.dhUrl("api/dashboard_hfc/actualizaciones.php", "frontend"),{
      cache:"no-store",
      headers:{"Accept":"application/json"}
    });
    const j=await r.json();
    if(!r.ok || j.ok===false)throw new Error(j.error||`HTTP ${r.status}`);

    const cmts=j.cmts||j.estado_red;
    const netcool=j.netcool;

    if(cmtsTime)cmtsTime.textContent=cmts?.iso?window.hfcSourceAge(cmts.iso):"Sin información";
    if(netTime)netTime.textContent=netcool?.iso?window.hfcSourceAge(netcool.iso):"Sin información";

    if(cmtsCard){
      cmtsCard.classList.remove("hfc-source-ok","hfc-source-warn","hfc-source-bad");
      cmtsCard.classList.add(hfcAutoAgeClass(cmts,"cmts"));
    }
    if(netCard){
      netCard.classList.remove("hfc-source-ok","hfc-source-warn","hfc-source-bad");
      netCard.classList.add(hfcAutoAgeClass(netcool,"netcool"));
    }
  }catch(err){
    if(cmtsTime)cmtsTime.textContent="No disponible";
    if(netTime)netTime.textContent="No disponible";
    if(cmtsCard)cmtsCard.classList.add("hfc-source-bad");
    if(netCard)netCard.classList.add("hfc-source-bad");
    console.warn("No fue posible actualizar cabecera HFC:",err);
  }
}
async function fetchJSON(url,opt={}){const r=await fetch(url,{cache:"no-store",...opt});const j=await r.json();if(!r.ok||j.ok===false)throw new Error(j.error||`HTTP ${r.status}`);return j}
let hfcRefreshing=false,hfcVersion=null;
async function refresh(){
  if(hfcRefreshing)return;
  hfcRefreshing=true;
  try{
    const [a,b]=await Promise.all([fetchJSON(API.estado),fetchJSON(API.inc)]);
    rows=a.rows||[];incs=b.rows||[];window.__HFC_EXEC_ALL_ROWS__=rows;loadFilters();apply();renderIncidents();
    $("liveStatus").textContent=`Base cargada · ${fmt(rows.length)} elementos · chequeo de cambios ${window.RKP_HFC_POLL_MS/1000} s`;
    window.dispatchEvent(new CustomEvent('rkp-hfc-data',{detail:{total:rows.length}}));
  }catch(e){$("liveStatus").textContent="No fue posible cargar: "+e.message;if(!rows.length)$("networkBody").innerHTML=`<tr><td colspan="13" class="hfc-empty">No fue posible leer la base local: ${esc(e.message)}. Importa la fuente o pulsa Actualizar para reintentar.</td></tr>`;}finally{hfcRefreshing=false;}
}
async function hfcPollChanges(){
  if(document.hidden || hfcRefreshing)return;
  try{
    const meta=await fetchJSON(window.dhUrl('api/dashboard_hfc/actualizaciones.php','frontend'));
    if(hfcVersion!==null && meta.version!==hfcVersion)await refresh();
    hfcVersion=meta.version;
    $("liveStatus").textContent=`Último chequeo: ${new Date().toLocaleString("es-CO",{timeZone:"America/Bogota"})} · base conservada · ${fmt(rows.length)} elementos`;
    await Promise.all([refreshHfcUpdateTimes(),refreshHfcAutoSourceHeader()]);
  }catch(e){$("liveStatus").textContent='No fue posible actualizar: '+e.message;}
}
function loadFilters(){
  const zones=[...new Set(rows.map(r=>r.zona).filter(Boolean))].sort();
  const cmts=[...new Set(rows.map(r=>r.cmts).filter(Boolean))].sort();
  const cv=$("fCmts").value,dv=$("zoneDetailSelect").value;
  $("fZone").innerHTML='<option value="">Todas</option>'+zones.map(x=>`<option>${esc(x)}</option>`).join("");
  $("fCmts").innerHTML='<option value="">Todos</option>'+cmts.map(x=>`<option>${esc(x)}</option>`).join("");
  $("zoneDetailSelect").innerHTML='<option value="">Seleccionar ciudad...</option>'+zones.map(x=>`<option>${esc(x)}</option>`).join("");
  if(cmts.includes(cv))$("fCmts").value=cv;if(zones.includes(dv))$("zoneDetailSelect").value=dv;
  zoneMultiRender();stateMultiRender();incMultiRender();
}
function apply(){
  const v=$("fVendor").value,c=$("fCmts").value,q=$("fSearch").value.trim().toUpperCase();
  filtered=rows.filter(r=>{
    if(selectedZone&&r.zona!==selectedZone)return false;if(v&&vendor(r)!==v)return false;if(selectedZones.size>0&&!selectedZones.has(r.zona))return false;if(c&&r.cmts!==c)return false;if(selectedStates.size>0&&!selectedStates.has(r.observacion))return false;if(selectedIncStatuses.size>0&&!selectedIncStatuses.has(r.inc_status))return false;
    if(q&&!`${vendor(r)} ${r.zona} ${r.cmts} ${r.service_group} ${r.ip} ${r.descripcion}`.toUpperCase().includes(q))return false;return true;
  });page=1;render();
}
function render(){
  renderKpis();renderTop10();renderZoneDetail();renderTable();
}
function renderKpis(){
  const aff=filtered.filter(affected),total=aff.filter(r=>totalAffectedState(r.observacion)).length,part=aff.filter(r=>partialAffectedState(r.observacion)).length;
  const without=aff.filter(r=>r.inc_status==='SIN INCIDENTE').length,withInc=aff.filter(r=>r.inc_status==='CON INCIDENTE').length;
  const data=[['Afectados',aff.length,`Total ${fmt(total)} · Parcial ${fmt(part)}`],['Sin incidente',without,`Afectados · con incidente ${fmt(withInc)}`],['Elementos en alcance',filtered.length,`Dataset completo ${fmt(rows.length)}`],['Fabricantes',`${fmt(filtered.filter(r=>vendor(r)==='CASA').length)} / ${fmt(filtered.filter(r=>vendor(r)==='ARRIS').length)}`,'CASA / ARRIS · alcance filtrado']];
  $('kpis').innerHTML=data.map(([label,value,detail])=>`<article class="kpi"><span>${label}</span><strong>${typeof value==='number'?fmt(value):value}</strong><small>${detail}</small></article>`).join('');
  const context=[$('fVendor').value,...selectedZones,$('fCmts').value,...selectedStates,...selectedIncStatuses,$('fSearch').value].filter(Boolean);
  $('hfcFilterContext').textContent=context.length?`Filtros: ${context.join(' · ')}`:'Sin filtros · dataset completo';
}
function renderTop10(){
  const priorityZones=new Set([
    "CALI","BUGA","BUENAVENTURA","CARTAGO","JAMUNDI","PALMIRA","TULUA","YUMBO",
    "PEREIRA","DOSQUEBRADAS","SANTA ROSA DE CABAL",
    "ARMENIA","CALARCA","MONTENEGRO","QUIMBAYA",
    "POPAYAN","SANTANDER DE QUILICHAO",
    "MANIZALES","CHINCHINA","LA DORADA"
  ]);
  const map={};rows.filter(r=>affected(r)&&priorityZones.has(String(r.zona||"").trim().toUpperCase())).forEach(r=>{const z=r.zona||"SIN ZONA";if(!map[z])map[z]={total:0,part:0,withInc:0,without:0};totalAffectedState(r.observacion)?map[z].total++:map[z].part++;r.inc_status==="CON INCIDENTE"?map[z].withInc++:map[z].without++});
  const top=Object.entries(map).sort((a,b)=>(b[1].total+b[1].part)-(a[1].total+a[1].part)).slice(0,10);
  $("top10").innerHTML=top.map(([z,x],idx)=>`<button class="top-row ${selectedZone===z?"active":""}" data-zone="${esc(z)}"><span class="rank">${idx+1}</span><div><strong>${esc(z)}</strong><small>${fmt(x.total+x.part)} afectados · Total ${fmt(x.total)} · Parcial ${fmt(x.part)}</small><small>Con INC ${fmt(x.withInc)} · Sin INC ${fmt(x.without)}</small></div><i class="fas fa-chevron-right"></i></button>`).join("");
  $("top10").querySelectorAll(".top-row").forEach(b=>b.onclick=()=>{selectedZone=b.dataset.zone;selectedZones=new Set([selectedZone]);zoneMultiRender();$("zoneDetailSelect").value=selectedZone;apply();});
}
function renderZoneDetail(){
  const z=$("zoneDetailSelect").value||selectedZone;if(!z){$("zoneDetail").className="hfc-zone-detail hfc-empty";$("zoneDetail").innerHTML="Selecciona una ciudad para ver su detalle.";return}
  const rr=rows.filter(r=>r.zona===z),aff=rr.filter(affected),tot=aff.filter(r=>totalAffectedState(r.observacion)).length,par=aff.length-tot,wi=aff.filter(r=>r.inc_status==="CON INCIDENTE").length,wo=aff.filter(r=>r.inc_status==="SIN INCIDENTE").length;
  const by={};rr.forEach(r=>{if(!by[r.cmts])by[r.cmts]={n:0,a:0,t:0,p:0,wi:0,wo:0};let x=by[r.cmts];x.n++;if(affected(r)){x.a++;totalAffectedState(r.observacion)?x.t++:x.p++;r.inc_status==="CON INCIDENTE"?x.wi++:x.wo++;}});
  const cmts=Object.entries(by).sort((a,b)=>b[1].a-a[1].a);
  $("zoneDetail").className="hfc-zone-detail";
  $("zoneDetail").innerHTML=`<div class="zone-title"><div><strong>${esc(z)}</strong><span>${fmt(rr.length)} elementos · ${fmt(new Set(rr.map(r=>r.cmts)).size)} CMTS</span></div></div>
  <div class="zone-kpis"><span><b>${fmt(aff.length)}</b>Afectados</span><span><b>${fmt(tot)}</b>Total</span><span><b>${fmt(par)}</b>Parcial</span><span><b>${fmt(wi)}</b>Con INC</span><span><b>${fmt(wo)}</b>Sin INC</span></div>
  <div class="cmts-list">${cmts.map(([c,x])=>`<button data-cmts="${esc(c)}"><strong>${esc(c)}</strong><span>${fmt(x.a)} afectados</span><small>T ${x.t} · P ${x.p} · INC ${x.wi} · Sin INC ${x.wo}</small></button>`).join("")}</div>`;
  $("zoneDetail").querySelectorAll("[data-cmts]").forEach(b=>b.onclick=()=>{selectedZones=new Set([z]);zoneMultiRender();$("fCmts").value=b.dataset.cmts;selectedZone="";apply();document.querySelector("#tabNetwork").scrollIntoView({behavior:"smooth"});});
}
function renderTable(){
  // Puente para la tabla ejecutiva: expone el arreglo filtrado desde
  // el mismo scope donde viven rows/filtered.
  window.__HFC_EXEC_CURRENT_ROWS__ = Array.isArray(filtered) ? filtered : [];
  const pages=Math.max(1,Math.ceil(filtered.length/PAGE));if(page>pages)page=pages;const slice=filtered.slice((page-1)*PAGE,page*PAGE);
  $('networkBody').innerHTML=slice.map((r,index)=>`<tr data-node="${esc(r.service_group)}" data-index="${(page-1)*PAGE+index}">
    <td><strong>${esc(r.service_group)}</strong><small>${esc(vendor(r))} · ${esc(r.tipo_elemento||'SERVICE GROUP')}</small></td>
    <td>${esc(r.cmts)}<small>${esc(r.ip||'')}</small></td>
    <td>${esc(r.zona)}</td><td>${badgeState(r.observacion)}</td>
    <td class="numeric">${fmt(r.total_modems)}</td><td class="numeric">${fmt(r.offline)}</td><td class="numeric">${(Number(r.porc_offline||0)*100).toFixed(1)}%</td>
    <td>${badgeInc(r)}</td><td>${esc(r.comunidad||'—')}</td><td>${esc(r.aliado||'—')}</td>
    <td>${esc(r.tipo_elemento||'SERVICE GROUP')}</td><td>${esc(vendor(r))}</td>
    <td class="hfc-desc" title="${esc(r.descripcion||'')}"><div class="hfc-desc-text">${esc(hfcDescripcionCorta(r.descripcion))}</div></td>
  </tr>`).join('');
  if(!slice.length)$('networkBody').innerHTML='<tr><td colspan="13" class="hfc-empty">Sin coincidencias. Revisa el alcance o pulsa Limpiar filtros.</td></tr>';
  $('networkBody').querySelectorAll('tr').forEach(tr=>{if(tr.children.length>1){tr.tabIndex=0;tr.setAttribute('aria-label','Ver ficha del nodo '+tr.dataset.node);}});
  $("networkCount").textContent=`${fmt(filtered.length)} registros`;$("pageInfo").textContent=`Página ${page} de ${pages}`;$("prev").disabled=page<=1;$("next").disabled=page>=pages;
  hfcHelixConsultarVisibles();
}
function renderIncidents(){
  $("incBody").innerHTML=incs.map(r=>`<tr>
    <td><span class="badge ${String(r.severity||"").toUpperCase()==="CRITICAL"?"bad":"review"}">${esc(r.severity||"—")}</span></td>
    <td>${esc(r.first_occurrence||[r.fecha_creacion,r.hora_creacion].filter(Boolean).join(" ")||"—")}</td>
    <td><strong>${esc(r.node_alias||r.elemento||"—")}</strong></td>
    <td>${esc(r.incidente||r.ttnumber_helix||"—")}</td>
    <td>${esc(r.municipio||r.zona||"—")}</td>
    <td>${esc(r.ttnumber||"—")}</td>
    <td>${esc(r.agent||"—")}</td>
    <td>${esc(r.tipo_afectacion||"—")}</td>
    <td><span class="badge ${r.cruce_hfc==="ALIAS_UNICO"?"ok":r.cruce_hfc==="ALIAS_AMBIGUO"?"warn":"neutral"}">${esc(r.cruce_hfc||"SIN CRUCE")}</span></td>
    <td>${esc(r.cmts||"—")}</td>
  </tr>`).join("");
}
function exportCSV(records,name,incident=false){
  const headers=incident?["SEVERITY","FIRST_OCCURRENCE","NODE_ALIAS","INCIDENTE","MUNICIPIO","TTNUMBER","AGENT","TIPO_AFECTACION","CRUCE_HFC","FABRICANTE","CMTS","SUMMARY"]:["FABRICANTE","ZONA","CMTS","IP","ELEMENTO","COMUNIDAD","ALIADO","TIPO_ELEMENTO","TOTAL_MODEMS","OFFLINE","PORC_OFFLINE","OBSERVACION","INC_STATUS","INCIDENTE","DESCRIPCION"];
  const rowsOut=records.map(r=>incident?[r.severity,r.first_occurrence,r.node_alias||r.elemento,r.incidente,r.municipio||r.zona,r.ttnumber,r.agent,r.tipo_afectacion,r.cruce_hfc,r.fabricante,r.cmts,r.summary]:[vendor(r),r.zona,r.cmts,r.ip,r.service_group,r.comunidad||"",r.aliado||"",r.tipo_elemento,r.total_modems,r.offline,(Number(r.porc_offline||0)*100).toFixed(1),r.observacion,r.inc_status,r.incidente,r.descripcion]);
  const q=v=>`"${String(v??"").replaceAll('"','""')}"`;const csv="\ufeff"+[headers,...rowsOut].map(x=>x.map(q).join(";")).join("\r\n");const blob=new Blob([csv],{type:"text/csv;charset=utf-8"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=name;a.click();URL.revokeObjectURL(a.href);
}
async function upload(file,url,resultEl){if(resultEl.dataset.busy)return;resultEl.dataset.busy="1";const button=url===API.base?$("btnImportBase"):$("btnImportInc");button.disabled=true;const fd=new FormData();fd.append("archivo",file);resultEl.textContent="Importando...";try{const j=await fetchJSON(url,{method:"POST",body:fd});resultEl.textContent=JSON.stringify(j,null,2);await refresh()}catch(e){resultEl.textContent="ERROR: "+e.message}finally{delete resultEl.dataset.busy;button.disabled=false}}

["fVendor","fCmts"].forEach(id=>$(id).onchange=apply);$("fSearch").oninput=apply;
$("zoneDetailSelect").onchange=()=>{selectedZone="";renderZoneDetail()};
$("btnClear").onclick=()=>{selectedZone="";selectedZones.clear();selectedStates.clear();selectedIncStatuses.clear();["fVendor","fCmts","fState","fInc"].forEach(id=>$(id).value="");$("fSearch").value="";zoneMultiRender();stateMultiRender();incMultiRender();apply()};
$("prev").onclick=()=>{if(page>1){page--;renderTable()}};$("next").onclick=()=>{if(page*PAGE<filtered.length){page++;renderTable()}};
$("btnExportVista").onclick=()=>exportCSV(filtered,`hfc_vista_${new Date().toISOString().slice(0,10)}.csv`);$("btnExportInc").onclick=()=>exportCSV(incs,`netcool_incidentes_${new Date().toISOString().slice(0,10)}.csv`,true);
$("btnRefresh").onclick=refresh;
$("btnOpenBase").onclick=()=>$("dlgBase").showModal();$("btnOpenInc").onclick=()=>$("dlgInc").showModal();
$("btnImportBase").onclick=()=>{const f=$("baseFile").files[0];if(f)upload(f,API.base,$("baseResult"))};
$("btnImportInc").onclick=()=>{const f=$("incFile").files[0];if(f)upload(f,API.incImport,$("incResult"))};
ensureHfcTableHeaders();ensureHfcAutoSourceHeader();
(async()=>{
 try{
  const meta=await fetchJSON(window.dhUrl('api/dashboard_hfc/actualizaciones.php','frontend'));
  hfcVersion=meta.version;
  await refresh();await Promise.all([refreshHfcUpdateTimes(),refreshHfcAutoSourceHeader()]);
 }catch(e){$("liveStatus").textContent='No fue posible cargar Dashboard HFC: '+e.message;}
})();
setInterval(hfcPollChanges,window.RKP_HFC_POLL_MS);

})();
/* ==== TABLA EJECUTIVA HFC V2 ==== */
(function(){
  if(window.__HFC_EXECUTIVE_TABLE_V2__) return;
  window.__HFC_EXECUTIVE_TABLE_V2__ = true;

  const ZONE_TO_DEPT = {
    "ARMENIA":"QUINDIO",
    "BARRANQUILLA":"ATLANTICO",
    "BOGOTA":"BOGOTA D.C.",
    "BUCARAMANGA":"SANTANDER",
    "BUGA":"VALLE",
    "CALI":"VALLE",
    "CARTAGENA":"BOLIVAR",
    "CHIA":"CUNDINAMARCA",
    "CUCUTA":"NORTE DE SANTANDER",
    "DORADAL":"ANTIOQUIA",
    "DOSQUEBRADAS":"RISARALDA",
    "DUITAMA":"BOYACA",
    "FUSAGASUGA":"CUNDINAMARCA",
    "GIRARDOT":"CUNDINAMARCA",
    "IBAGUE":"TOLIMA",
    "JAMUNDI":"VALLE",
    "MADRID":"CUNDINAMARCA",
    "MANIZALES":"CALDAS",
    "MEDELLIN":"ANTIOQUIA",
    "MONTERIA":"CORDOBA",
    "NEIVA":"HUILA",
    "PALMIRA":"VALLE",
    "PASTO":"NARINO",
    "PEREIRA":"RISARALDA",
    "POPAYAN":"CAUCA",
    "RIOHACHA":"LA GUAJIRA",
    "SANTA MARTA":"MAGDALENA",
    "SINCELEJO":"SUCRE",
    "SOACHA":"CUNDINAMARCA",
    "SOGAMOSO":"BOYACA",
    "SOLEDAD":"ATLANTICO",
    "TULUA":"VALLE",
    "TUNJA":"BOYACA",
    "VALLEDUPAR":"CESAR",
    "VILLAVICENCIO":"META",
    "YOPAL":"CASANARE",
    "ZIPAQUIRA":"CUNDINAMARCA"
  };

  const DEPT_TO_CAPITAL = {
    "ANTIOQUIA":"MEDELLIN",
    "ATLANTICO":"BARRANQUILLA",
    "BOGOTA D.C.":"BOGOTA",
    "BOLIVAR":"CARTAGENA",
    "BOYACA":"TUNJA",
    "CALDAS":"MANIZALES",
    "CASANARE":"YOPAL",
    "CAUCA":"POPAYAN",
    "CESAR":"VALLEDUPAR",
    "CORDOBA":"MONTERIA",
    "CUNDINAMARCA":"BOGOTA",
    "HUILA":"NEIVA",
    "LA GUAJIRA":"RIOHACHA",
    "MAGDALENA":"SANTA MARTA",
    "META":"VILLAVICENCIO",
    "NARINO":"PASTO",
    "NORTE DE SANTANDER":"CUCUTA",
    "QUINDIO":"ARMENIA",
    "RISARALDA":"PEREIRA",
    "SANTANDER":"BUCARAMANGA",
    "SUCRE":"SINCELEJO",
    "TOLIMA":"IBAGUE",
    "VALLE":"CALI"
  };

  function norm(v){
    return String(v||"").replace(/\u00a0/g," ").trim().toUpperCase();
  }

  function pct(n,d){
    if(!d) return "0,00%";
    return ((n*100)/d).toFixed(2).replace(".",",")+"%";
  }

  function isAffected(estado){
    const e=norm(estado).replace(/_/g," ");
    return e==="DESENGANCHE PARCIAL" || e==="DESENGANCHE TOTAL" || e==="POSIBLE DESENGANCHE TOTAL / HISTORICO" || e==="POSIBLE CAIDA PROLONGADA / HISTORICO";
  }

  function currentRows(){
    if(Array.isArray(window.__HFC_EXEC_CURRENT_ROWS__)){
      return window.__HFC_EXEC_CURRENT_ROWS__;
    }
    return [];
  }

  function zoneOf(r){
    return norm(r?.zona ?? r?.ZONA ?? "");
  }

  function stateOf(r){
    return norm(r?.observacion ?? r?.OBSERVACION ?? r?.estado ?? r?.ESTADO ?? "");
  }

  function buildSummary(data){
    const zoneMap=new Map();

    data.forEach(r=>{
      const zona=zoneOf(r);
      if(!zona) return;
      if(!zoneMap.has(zona)) zoneMap.set(zona,{total:0,affected:0});
      const x=zoneMap.get(zona);
      x.total++;
      if(isAffected(stateOf(r))) x.affected++;
    });

    const deptMap=new Map();
    zoneMap.forEach((x,zona)=>{
      const dept=ZONE_TO_DEPT[zona];
      if(!dept) return;
      if(!deptMap.has(dept)) deptMap.set(dept,{total:0,affected:0});
      const d=deptMap.get(dept);
      d.total+=x.total;
      d.affected+=x.affected;
    });

    const PRIORITY_DEPTS=["VALLE","RISARALDA","QUINDIO","CAUCA","CALDAS"];
    const ordered=PRIORITY_DEPTS.map(dept=>[
      dept,
      deptMap.get(dept)||{total:0,affected:0}
    ]);

    return {zoneMap,deptMap,ordered};
  }

  function getMainTable(){
    const body=document.getElementById("networkBody");
    return body ? body.closest("table") : null;
  }

  function ensurePanel(){return document.getElementById("hfcExecutivePanel");}

  function renderExecutiveTable(){
    const panel=ensurePanel();
    if(!panel) return;

    const body=panel.querySelector("#hfcExecutiveBody");
    const subtitle=panel.querySelector("#hfcExecutiveSubtitle");
    const data=(Array.isArray(window.__HFC_EXEC_ALL_ROWS__) && window.__HFC_EXEC_ALL_ROWS__.length) ? window.__HFC_EXEC_ALL_ROWS__ : currentRows();
    const info=buildSummary(data);

    subtitle.textContent=`Resumen regional independiente de filtros · Valle, Risaralda, Quindío, Cauca y Caldas · ${data.length.toLocaleString("es-CO")} nodos base.`;

    if(!info.ordered.length){
      body.innerHTML='<tr class="hfc-empty-row"><td colspan="5">No hay departamentos reconocidos dentro de la vista filtrada actual.</td></tr>';
      return;
    }

    const html=[];
    info.ordered.forEach(([dept,d])=>{
      html.push(`
        <tr class="hfc-dept-row">
          <td class="hfc-left">DEPARTAMENTO</td>
          <td class="hfc-left">${dept}</td>
          <td>${d.total.toLocaleString("es-CO")}</td>
          <td>${d.affected.toLocaleString("es-CO")}</td>
          <td>${pct(d.affected,d.total)}</td>
        </tr>`);

      const HFC_CAPITAL_PRIORITARIA={
        "VALLE":"CALI",
        "RISARALDA":"PEREIRA",
        "QUINDIO":"ARMENIA",
        "CAUCA":"POPAYAN",
        "CALDAS":"MANIZALES"
      };
      const capital=HFC_CAPITAL_PRIORITARIA[dept];
      const c=capital ? (info.zoneMap.get(capital)||{total:0,affected:0}) : null;
      if(c){
        html.push(`
          <tr class="hfc-capital-row">
            <td class="hfc-left">CAPITAL</td>
            <td class="hfc-left">${capital}</td>
            <td>${c.total.toLocaleString("es-CO")}</td>
            <td>${c.affected.toLocaleString("es-CO")}</td>
            <td>${pct(c.affected,c.total)}</td>
          </tr>`);
      }
    });

    body.innerHTML=html.join("");
  }

  window.addEventListener('rkp-hfc-data',renderExecutiveTable);
})();
/* ==== FIN TABLA EJECUTIVA HFC V2 ==== */


/* BEGIN HFC ANALYTICS NACIONAL V1 */
/* BEGIN HFC ANALYTICS NACIONAL V1 */
(function(){
  "use strict";

  const app=document.getElementById("hfcApp");
  if(!app || !app.dataset.apiAnalytics) return;

  const API=app.dataset.apiAnalytics;
  const $=id=>document.getElementById(id);

  const fmt=n=>
    new Intl.NumberFormat("es-CO")
      .format(Number(n||0));

  const esc=s=>String(s??"").replace(
    /[&<>"']/g,
    m=>({
      "&":"&amp;",
      "<":"&lt;",
      ">":"&gt;",
      '"':"&quot;",
      "'":"&#39;"
    }[m])
  );

  const ANALYTICS_PAGE_SIZE=100;
  const ANALYTICS_EXPORT_BATCH=5000;

  let analyticsOffset=0;
  let analyticsPage=1;
  let analyticsTotalPages=1;
  let analyticsTotalRows=0;
  let analyticsCurrentItems=[];
  let analyticsSummary=null;
  let analyticsCmtsItems=[];


  function num(v,digits=1){

    const n=Number(v);

    if(!Number.isFinite(n)){
      return "—";
    }

    return n.toLocaleString(
      "es-CO",
      {
        minimumFractionDigits:digits,
        maximumFractionDigits:digits
      }
    );
  }


  async function get(resource,params={}){

    const q=new URLSearchParams({
      resource,
      ...params
    });

    const r=await fetch(
      `${API}${API.includes("?") ? "&" : "?"}${q.toString()}`,
      {
        cache:"no-store",
        headers:{
          "Accept":"application/json"
        }
      }
    );

    let j={};

    try{
      j=await r.json();
    }catch(e){

      throw new Error(
        `Respuesta inválida HTTP ${r.status}`
      );
    }

    if(!r.ok || j.ok===false){

      throw new Error(
        j.error ||
        j.detail?.error ||
        `HTTP ${r.status}`
      );
    }

    return j;
  }


  function renderSummary(j){

    const data=[
      ["CMTS total",j.cmts_total],
      ["CASA",j.cmts_casa],
      ["ARRIS",j.cmts_arris],
      ["Nodos total",j.nodes_total],
      ["Nodos CASA",j.nodes_casa],
      ["Nodos ARRIS",j.nodes_arris]
    ];

    $("hfcAnalyticsKpis").innerHTML=
      data.map(([label,value])=>`

        <article class="hfc-analytics-kpi">

          <span>
            ${esc(label)}
          </span>

          <strong>
            ${fmt(value)}
          </strong>

        </article>

      `).join("");
  }


  async function loadSummary(){

    const j=await get("resumen");

    analyticsSummary=j;

    renderSummary(j);

    $("hfcAnalyticsUpdated").textContent=
      `Actualizado ${
        new Date().toLocaleTimeString("es-CO")
      }`;
  }


  async function loadCmts(){

    const tech=
      $("haTechnology").value;

    const current=
      $("haCmts").value;

    const j=await get(
      "cmts",
      tech
        ? {technology:tech}
        : {}
    );

    const items=
      Array.isArray(j.items)
        ? j.items
        : [];

    analyticsCmtsItems=items;

    const names=[
      ...new Set(
        items
          .map(x=>
            String(
              x.cmts ||
              x.name ||
              x.cmts_name ||
              ""
            ).trim()
          )
          .filter(Boolean)
      )
    ].sort();


    $("haCmts").innerHTML=
      '<option value="">Todos</option>' +

      names.map(x=>
        `<option value="${esc(x)}">
          ${esc(x)}
        </option>`
      ).join("");


    if(names.includes(current)){
      $("haCmts").value=current;
    }
  }


  function renderNodes(items){

    const body=
      $("hfcAnalyticsBody");


    if(!items.length){

      body.innerHTML=
        `
        <tr>
          <td
            colspan="14"
            class="hfc-analytics-empty"
          >
            Sin resultados.
          </td>
        </tr>
        `;

      $("hfcAnalyticsCount")
        .textContent="0 nodos";

      return;
    }


    const safe=v=>
      (
        v===null ||
        v===undefined ||
        v===""
      )
        ? "N/D"
        : v;


    const metric=(v,d=2)=>
      (
        v===null ||
        v===undefined ||
        v===""
      )
        ? "N/D"
        : Number(v).toFixed(d);


    const hogares=v=>
      (
        v===null ||
        v===undefined ||
        v===""
      )
        ? "N/D"
        : fmt(v);


    // ATLAS_HFC_QOE_OFFLINE_V1
    const qoeMetric=v=>
      (
        v===null ||
        v===undefined ||
        v===""
      )
        ? "—"
        : Number(v).toFixed(0);


    body.innerHTML=
      items.map(r=>`

        <tr>

          <td>

            <span
              class="vendor ${
                String(
                  r.tecnologia || ""
                ).toLowerCase()
              }"
            >

              ${esc(
                safe(r.tecnologia)
              )}

            </span>

          </td>


          <td>
            ${esc(safe(r.cmts))}
          </td>


          <td>
            ${esc(safe(r.zona))}
          </td>


          <td>

            <strong>
              ${esc(safe(r.nodo))}
            </strong>

          </td>


          <td>
            ${hogares(r.hogares)}
          </td>


          <td>
            ${hogares(r.offline)}
          </td>


          <td>

            <span
              class="
                hfc-analytics-state
                state-${
                  String(
                    r.estado || "nd"
                  ).toLowerCase()
                }
              "
            >

              ${esc(
                safe(r.estado)
              )}

            </span>

          </td>


          <td>
            ${metric(r.fec_pct,2)}
          </td>


          <td>
            ${metric(r.ufec_pct,2)}
          </td>


          <td>
            ${metric(r.snr_up,1)}
          </td>


          <td>
            ${metric(
              r.signal_quality,
              1
            )}
          </td>


          <td>
            ${qoeMetric(
              r.qoe
            )}
          </td>


          <td>
            ${
              metric(
                Number(
                  r.dias_estado
                ) * 24,
                2
              )
            }
          </td>


          <td>
            ${
              esc(
                safe(
                  r.estado_operativo_hfc_auto
                )
              )
            }
          </td>


          <td>
            ${
              esc(
                safe(
                  r.fecha_hfc_auto
                )
              )
            }
          </td>

        </tr>

      `).join("");


    $("hfcAnalyticsCount")
      .textContent=
        `${fmt(items.length)} nodos mostrados`;
  }


  function resetAnalyticsPage(){

    analyticsPage=1;
    analyticsOffset=0;
  }


  function getNodeParams(
    limit=ANALYTICS_PAGE_SIZE,
    offset=analyticsOffset
  ){

    const params={
      limit:String(limit),
      offset:String(offset)
    };


    const tech=
      $("haTechnology")?.value || "";

    const cmts=
      $("haCmts")?.value || "";

    const search=
      $("haSearch")?.value.trim() || "";


    if(tech){
      params.technology=tech;
    }

    if(cmts){
      params.cmts=cmts;
    }

    if(search){
      params.search=search;
    }


    return params;
  }


  function resolveAnalyticsTotal(
    j,
    items
  ){

    /*
     * Si en algún momento el backend
     * devuelve el total filtrado,
     * tiene prioridad.
     */

    const backendTotal=
      Number(
        j.total ??
        j.total_count ??
        j.records_total ??
        j.filtered_total ??
        0
      );


    if(
      Number.isFinite(
        backendTotal
      ) &&
      backendTotal>0
    ){

      return backendTotal;
    }


    const tech=
      $("haTechnology")?.value || "";

    const cmts=
      $("haCmts")?.value || "";

    const search=
      $("haSearch")
        ?.value
        .trim() || "";


    /*
     * BÚSQUEDA LIBRE
     *
     * El backend actual no entrega
     * total del search.
     *
     * Si llegamos a una página con
     * menos de 100, ahí sí conocemos
     * el total real.
     */

    if(search){

      if(
        items.length <
        ANALYTICS_PAGE_SIZE
      ){

        return (
          analyticsOffset +
          items.length
        );
      }

      return 0;
    }


    /*
     * CMTS
     *
     * /cmts ya nos entrega
     * cuántos nodos tiene cada CMTS.
     */

    if(cmts){

      const row=
        analyticsCmtsItems.find(x=>

          String(
            x.cmts ||
            x.name ||
            x.cmts_name ||
            ""
          ).trim()===cmts

        );


      const total=
        Number(
          row?.nodes
        );


      if(
        Number.isFinite(total) &&
        total>=0
      ){

        return total;
      }
    }


    /*
     * TECNOLOGÍA / NACIONAL
     *
     * El resumen ya trae:
     *
     * nodes_total
     * nodes_casa
     * nodes_arris
     */

    if(analyticsSummary){

      if(tech==="CASA"){

        const total=
          Number(
            analyticsSummary.nodes_casa
          );

        if(
          Number.isFinite(total)
        ){

          return total;
        }
      }


      if(tech==="ARRIS"){

        const total=
          Number(
            analyticsSummary.nodes_arris
          );

        if(
          Number.isFinite(total)
        ){

          return total;
        }
      }


      if(
        !tech &&
        !cmts
      ){

        const total=
          Number(
            analyticsSummary.nodes_total
          );

        if(
          Number.isFinite(total)
        ){

          return total;
        }
      }
    }


    /*
     * Último fallback.
     */

    if(
      items.length <
      ANALYTICS_PAGE_SIZE
    ){

      return (
        analyticsOffset +
        items.length
      );
    }


    return 0;
  }


  function updateAnalyticsPagination(
    items,
    total
  ){

    const info=
      $("haPageInfo");

    const prev=
      $("haPrev");

    const next=
      $("haNext");


    analyticsTotalRows=
      Number(total) || 0;


    if(
      analyticsTotalRows>0
    ){

      analyticsTotalPages=
        Math.max(
          1,
          Math.ceil(
            analyticsTotalRows /
            ANALYTICS_PAGE_SIZE
          )
        );

    }else{

      /*
       * Para búsquedas donde todavía
       * desconocemos el total.
       */

      analyticsTotalPages=
        items.length===
        ANALYTICS_PAGE_SIZE

          ? analyticsPage+1

          : analyticsPage;
    }


    /*
     * TEXTO:
     *
     * Página 1 de 121
     */

    if(info){

      if(
        analyticsTotalRows>0
      ){

        info.textContent=
          `Página ${analyticsPage} de ${analyticsTotalPages}`;

      }else{

        info.textContent=
          `Página ${analyticsPage}`;
      }
    }


    /*
     * ANTERIOR
     */

    if(prev){

      prev.disabled=
        analyticsPage<=1;
    }


    /*
     * SIGUIENTE
     */

    if(next){

      if(
        analyticsTotalRows>0
      ){

        next.disabled=
          analyticsPage>=
          analyticsTotalPages;

      }else{

        next.disabled=
          items.length <
          ANALYTICS_PAGE_SIZE;
      }
    }
  }


  async function loadNodes(){

    const params=
      getNodeParams();


    $("hfcAnalyticsBody")
      .innerHTML=
        `
        <tr>
          <td colspan="14">
            Consultando HFC Analytics...
          </td>
        </tr>
        `;


    try{

      const j=
        await get(
          "nodos",
          params
        );


      const items=
        Array.isArray(j.items)
          ? j.items
          : [];


      analyticsCurrentItems=
        items;


      renderNodes(items);


      const total=
        resolveAnalyticsTotal(
          j,
          items
        );


      updateAnalyticsPagination(
        items,
        total
      );


    }catch(err){

      $("hfcAnalyticsBody")
        .innerHTML=
          `
          <tr>

            <td
              colspan="14"
              class="hfc-analytics-error"
            >

              ERROR:
              ${esc(err.message)}

            </td>

          </tr>
          `;


      $("hfcAnalyticsCount")
        .textContent="";
    }
  }


  async function exportAnalyticsCsv(){

    const button=
      $("haExportCsv");


    if(button){

      button.disabled=true;

      button.innerHTML=
        `
        <i
          class="fas fa-spinner fa-spin"
        ></i>

        Exportando...
        `;
    }


    try{

      const allItems=[];

      let offset=0;


      while(true){

        const params=
          getNodeParams(
            ANALYTICS_EXPORT_BATCH,
            offset
          );


        const j=
          await get(
            "nodos",
            params
          );


        const items=
          Array.isArray(j.items)
            ? j.items
            : [];


        allItems.push(
          ...items
        );


        if(
          items.length <
          ANALYTICS_EXPORT_BATCH
        ){

          break;
        }


        offset+=
          ANALYTICS_EXPORT_BATCH;
      }


      if(
        !allItems.length
      ){

        $("hfcAnalyticsCount").textContent="No hay registros para exportar.";

        return;
      }


      const headers=[

        "Tecnología",
        "CMTS",
        "Zona",
        "Nodo",
        "Hogares",
        "Estado",
        "FEC %",
        "uFEC %",
        "SNR UP",
        "SQ",
        "QoE",
        "Horas estado",
        "HFC AUTO",
        "Actualización"

      ];


      const rowsOut=
        allItems.map(r=>[

          r.tecnologia ?? "",
          r.cmts ?? "",
          r.zona ?? "",
          r.nodo ?? "",
          r.hogares ?? "",
          r.estado ?? "",
          r.fec_pct ?? "",
          r.ufec_pct ?? "",
          r.snr_up ?? "",
          r.signal_quality ?? "",
          r.qoe ?? "",

          (
            r.dias_estado!==null &&
            r.dias_estado!==undefined &&
            r.dias_estado!==""
          )

            ? (
                Number(
                  r.dias_estado
                ) * 24
              ).toFixed(2)

            : "",

          r.estado_operativo_hfc_auto ?? "",

          r.fecha_hfc_auto ?? ""

        ]);


      const csvValue=v=>
        `"${String(v??"")
          .replaceAll(
            '"',
            '""'
          )}"`;


      const csv=
        "\ufeff" +

        [headers,...rowsOut]

          .map(row=>
            row
              .map(csvValue)
              .join(";")
          )

          .join("\r\n");


      const blob=
        new Blob(
          [csv],
          {
            type:
              "text/csv;charset=utf-8"
          }
        );


      const url=
        URL.createObjectURL(
          blob
        );


      const a=
        document.createElement(
          "a"
        );


      a.href=url;


      a.download=
        `hfc_analytics_${
          new Date()
            .toISOString()
            .slice(0,10)
        }.csv`;


      document.body
        .appendChild(a);


      a.click();


      a.remove();


      URL.revokeObjectURL(
        url
      );


    }catch(err){

      console.error(
        "Error exportando HFC Analytics:",
        err
      );


      $("hfcAnalyticsCount").textContent="No fue posible exportar: "+err.message;


    }finally{

      if(button){

        button.disabled=false;

        button.innerHTML=
          `
          <i
            class="fas fa-download"
          ></i>

          Exportar CSV
          `;
      }
    }
  }


  async function refreshAll(){

    try{

      resetAnalyticsPage();


      await Promise.all([

        loadSummary(),
        loadCmts()

      ]);


      await loadNodes();


    }catch(err){

      $("hfcAnalyticsUpdated")
        .textContent=
          "No disponible";


      $("hfcAnalyticsBody")
        .innerHTML=
          `
          <tr>

            <td
              colspan="14"
              class="hfc-analytics-error"
            >

              ERROR:
              ${esc(err.message)}

            </td>

          </tr>
          `;


      console.error(
        "HFC Analytics:",
        err
      );
    }
  }


  /*
   * CAMBIO DE TECNOLOGÍA
   */

  $("haTechnology")
    ?.addEventListener(
      "change",
      async()=>{

        resetAnalyticsPage();

        await loadCmts();

        await loadNodes();
      }
    );


  /*
   * CAMBIO DE CMTS
   */

  $("haCmts")
    ?.addEventListener(
      "change",
      ()=>{

        resetAnalyticsPage();

        loadNodes();
      }
    );


  /*
   * BOTÓN CONSULTAR
   */

  $("haRefresh")
    ?.addEventListener(
      "click",
      refreshAll
    );


  /*
   * ANTERIOR
   */

  $("haPrev")
    ?.addEventListener(
      "click",
      ()=>{

        if(
          analyticsPage<=1
        ){
          return;
        }


        analyticsPage--;


        analyticsOffset=
          (
            analyticsPage-1
          ) *
          ANALYTICS_PAGE_SIZE;


        loadNodes();
      }
    );


  /*
   * SIGUIENTE
   */

  $("haNext")
    ?.addEventListener(
      "click",
      ()=>{

        /*
         * Si sabemos el total,
         * evitamos pasar la última.
         */

        if(
          analyticsTotalRows>0 &&
          analyticsPage>=
          analyticsTotalPages
        ){

          return;
        }


        /*
         * Si todavía no sabemos el
         * total, seguimos mientras
         * lleguen páginas completas.
         */

        if(
          analyticsTotalRows<=0 &&
          analyticsCurrentItems.length <
          ANALYTICS_PAGE_SIZE
        ){

          return;
        }


        analyticsPage++;


        analyticsOffset=
          (
            analyticsPage-1
          ) *
          ANALYTICS_PAGE_SIZE;


        loadNodes();
      }
    );


  /*
   * EXPORTAR CSV
   */

  $("haExportCsv")
    ?.addEventListener(
      "click",
      exportAnalyticsCsv
    );


  /*
   * BUSCADOR
   */

  let searchTimer=null;


  $("haSearch")
    ?.addEventListener(
      "input",
      ()=>{

        clearTimeout(
          searchTimer
        );


        resetAnalyticsPage();


        searchTimer=
          setTimeout(
            loadNodes,
            450
          );
      }
    );


  /*
   * CARGA INICIAL
   */

  let analyticsLoaded=false, analyticsLoading=false;
  window.addEventListener('rkp-hfc-tab',async e=>{
    if(e.detail==='analytics' && !analyticsLoaded && !analyticsLoading){
      analyticsLoading=true;await refreshAll();analyticsLoaded=true;analyticsLoading=false;
    }
  });


})();
/* END HFC ANALYTICS NACIONAL V1 */


/* QoE source metadata uses the existing lightweight endpoint. */
(() => {
  async function refreshQoeStamp(){
    const el=document.getElementById('hfcQoeUpdated');
    try{
      const r=await fetch(window.dhUrl('api/dashboard_hfc/qoe_actualizacion.php','frontend'),{cache:'no-store'});
      const data=await r.json();
      if(!r.ok || data.ok===false)throw new Error(data.error||`HTTP ${r.status}`);
      el.textContent=data.available && data.updated_at_iso ? window.hfcSourceAge(data.updated_at_iso) : 'No disponible';
    }catch(e){el.textContent='No disponible';}
  }
  refreshQoeStamp();setInterval(refreshQoeStamp,60000);
})();
(() => {
"use strict";

const app = document.getElementById("hfcApp");
if (!app) return;

const API = window.dhUrl("backend/api/hfc/rf_proxy.php");
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
const fmt = n => new Intl.NumberFormat("es-CO").format(Number(n || 0));
const nd = v => (v === null || v === undefined || v === "") ? "N/D" : v;
const n1 = v => (v === null || v === undefined || v === "") ? "N/D" : Number(v).toFixed(1);
const n2 = v => (v === null || v === undefined || v === "") ? "N/D" : Number(v).toFixed(2);

let rfLoading=false;
let summary = null;
let ranking = [];
let selected = null;
let spectrumGroups = new Map();
let spectrumMode = "actual";

async function get(action, params={}) {
  const qs = new URLSearchParams({op:action, ...params});
  const r = await fetch(`${API}${API.includes("?") ? "&" : "?"}${qs}`, {cache:"no-store", headers:{"Accept":"application/json"}});
  let j;
  try { j = await r.json(); } catch { throw new Error(`Respuesta no JSON (${r.status})`); }
  if (!r.ok || j.ok === false) throw new Error(j?.detail?.error || j.error || `HTTP ${r.status}`);
  return j;
}

function activateTab(name) {
  const panels = {network:$("tabNetwork"),incidents:$("tabIncidents"),analytics:$("hfcAnalyticsPanel"),rf:$("tabRf")};
  document.querySelectorAll(".hfc-tab").forEach(b => {b.classList.toggle("active", b.dataset.tab === name);b.setAttribute("aria-selected",String(b.dataset.tab===name));b.tabIndex=b.dataset.tab===name?0:-1;});
  Object.entries(panels).forEach(([key,p]) => { if (p) p.classList.toggle("active", key === name); });
  window.dispatchEvent(new CustomEvent("rkp-hfc-tab",{detail:name}));
  if (name === "rf") loadRf();
}

const tabs=[...document.querySelectorAll('.hfc-tab')];
tabs.forEach((b,i)=>{
  b.setAttribute('role','tab');b.id='hfcTab-'+b.dataset.tab;
  const target={network:'tabNetwork',incidents:'tabIncidents',analytics:'hfcAnalyticsPanel',rf:'tabRf'}[b.dataset.tab];
  b.setAttribute('aria-controls',target);$(target).setAttribute('role','tabpanel');$(target).setAttribute('aria-labelledby',b.id);
  b.setAttribute('aria-selected',String(i===0));b.tabIndex=i===0?0:-1;
  b.onclick=()=>activateTab(b.dataset.tab);
  b.onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;tabs[next].focus();activateTab(tabs[next].dataset.tab);}};
});

function coveragePct(key) {
  if (!summary?.upstreams_total) return 0;
  return Math.round(((summary.coverage?.[key] || 0) / summary.upstreams_total) * 1000) / 10;
}

function renderKpis() {
  const items = [
    ["Upstreams",summary.upstreams_total,"Cobertura nacional"],
    ["CNR",summary.coverage?.cnr,`${coveragePct("cnr")}% cobertura`],
    ["SQ",summary.coverage?.signal_quality,`${coveragePct("signal_quality")}% cobertura`],
    ["FEC / uFEC",Math.min(summary.coverage?.fec_pct||0,summary.coverage?.ufec_pct||0),`${Math.min(coveragePct("fec_pct"),coveragePct("ufec_pct"))}% cobertura`],
    ["Utilización",summary.coverage?.utilization,`${coveragePct("utilization")}% cobertura`],
    ["Impair",summary.coverage?.impair,`${coveragePct("impair")}% cobertura`],
    ["Spectrum",summary.spectrum_points,`${summary.spectrum_upstreams||0} upstreams`]
  ];
  $("rfKpis").innerHTML = items.map(([a,b,c]) => `
    <article class="rf-kpi"><span>${esc(a)}</span><strong>${fmt(b)}</strong><small>${esc(c)}</small></article>
  `).join("");
}

function ensureSelectionStrip() {
  if ($("rfSelectedMetrics")) return;
  const toolbar = document.querySelector("#tabRf .rf-toolbar");
  if (!toolbar) return;

  const strip = document.createElement("div");
  strip.id = "rfSelectedMetrics";
  strip.className = "rf-selected-metrics";
  strip.innerHTML = `
    <article><span>CNR</span><strong id="selCnr">—</strong></article>
    <article><span>SQ</span><strong id="selSq">—</strong></article>
    <article><span>FEC</span><strong id="selFec">—</strong></article>
    <article><span>uFEC</span><strong id="selUfec">—</strong></article>
    <article><span>Utilización</span><strong id="selUtil">—</strong></article>
    <article><span>Impair</span><strong id="selImpair">—</strong></article>
    <article><span>Score</span><strong id="selScore">—</strong></article>
  `;
  toolbar.insertAdjacentElement("afterend", strip);
}

function updateSelectionStrip(row) {
  ensureSelectionStrip();
  const set = (id,v) => { const el=$(id); if(el) el.textContent=v; };
  if (!row) {
    ["selCnr","selSq","selFec","selUfec","selUtil","selImpair","selScore"].forEach(id=>set(id,"—"));
    return;
  }
  set("selCnr",`${n1(row.cnr)} dB`);
  set("selSq",`${n1(row.signal_quality)} dB`);
  set("selFec",`${n2(row.fec_pct)}%`);
  set("selUfec",`${n2(row.ufec_pct)}%`);
  set("selUtil",`${n1(row.utilization)}%`);
  set("selImpair",Number(row.impair||0)===1?"ACTIVO":"NO");
  set("selScore",n1(row.score));
}

function prepCanvas(canvas, minHeight=250) {
  const ctx=canvas.getContext("2d");
  const rect=canvas.getBoundingClientRect();
  const dpr=window.devicePixelRatio||1;
  const cssW=Math.max(420,rect.width||720);
  const cssH=Math.max(minHeight,rect.height||minHeight);
  canvas.width=Math.round(cssW*dpr); canvas.height=Math.round(cssH*dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,cssW,cssH);
  return {ctx,w:cssW,h:cssH};
}

function drawHorizontalMetric(canvas, rows, key, unit="", maxHint=null) {
  const data=rows.filter(r=>Number.isFinite(Number(r[key]))).slice(0,15);
  const {ctx,w,h}=prepCanvas(canvas,260);
  ctx.font="11px Segoe UI"; ctx.fillStyle="#667085";

  if(!data.length){ ctx.fillText("Sin datos disponibles",18,30); return; }

  const pad={l:130,r:44,t:18,b:28};
  const values=data.map(r=>Number(r[key]));
  let max=Math.max(...values);
  if(maxHint!==null) max=Math.max(max,maxHint);
  if(max<=0) max=1;
  const rowH=(h-pad.t-pad.b)/data.length;

  for(let i=0;i<=4;i++){
    const x=pad.l+i*(w-pad.l-pad.r)/4;
    ctx.strokeStyle="#e5e7eb";ctx.beginPath();ctx.moveTo(x,pad.t);ctx.lineTo(x,h-pad.b);ctx.stroke();
    ctx.fillStyle="#98a2b3";ctx.fillText((i*max/4).toFixed(max>20?0:1),x-8,h-8);
  }

  data.forEach((r,i)=>{
    const v=Number(r[key]);
    const y=pad.t+i*rowH+rowH*.23;
    const bh=Math.max(6,rowH*.52);
    const bw=(v/max)*(w-pad.l-pad.r);

    ctx.fillStyle="#eef2f7"; ctx.fillRect(pad.l,y,w-pad.l-pad.r,bh);
    ctx.fillStyle="#2f61d5"; ctx.fillRect(pad.l,y,bw,bh);

    ctx.fillStyle="#344054";
    const name=`${r.nodo||"—"} · ${r.upstream||"—"}`;
    ctx.fillText(name.length>19?name.slice(0,18)+"…":name,6,y+bh-1);
    ctx.fillStyle="#101828";ctx.font="600 11px Segoe UI";
    ctx.fillText(`${v.toFixed(key.includes("fec")?2:1)}${unit}`,Math.min(w-pad.r-54,pad.l+bw+6),y+bh-1);
    ctx.font="11px Segoe UI";
  });
}

function drawImpairSummary(canvas, rows) {
  const {ctx,w,h}=prepCanvas(canvas,260);
  const total=rows.length||1;
  const active=rows.filter(r=>Number(r.impair||0)===1).length;
  const inactive=total-active;

  ctx.font="12px Segoe UI";ctx.fillStyle="#667085";
  ctx.fillText("Upstreams visibles en la selección",18,26);

  const x=40,y=82,bw=w-80,bh=34;
  ctx.fillStyle="#e8f5ec";ctx.fillRect(x,y,bw,bh);
  const aw=bw*(active/total);
  ctx.fillStyle="#e5484d";ctx.fillRect(x,y,aw,bh);

  ctx.fillStyle="#101828";ctx.font="700 27px Segoe UI";ctx.fillText(String(active),40,160);
  ctx.font="11px Segoe UI";ctx.fillStyle="#667085";ctx.fillText("Impair activo",40,180);

  ctx.fillStyle="#101828";ctx.font="700 27px Segoe UI";ctx.fillText(String(inactive),w/2,160);
  ctx.font="11px Segoe UI";ctx.fillStyle="#667085";ctx.fillText("Sin impair",w/2,180);

  ctx.fillStyle="#667085";ctx.font="11px Segoe UI";
  ctx.fillText(`${((active/total)*100).toFixed(1)}% activos`,40,216);
}

function renderCharts(rows) {
  drawHorizontalMetric($("cnrChart"),rows,"cnr"," dB",50);
  drawHorizontalMetric($("sqChart"),rows,"signal_quality"," dB",50);
  drawHorizontalMetric($("fecChart"),rows,"fec_pct","%",100);
  drawHorizontalMetric($("ufecChart"),rows,"ufec_pct","%",100);
  drawHorizontalMetric($("utilChart"),rows,"utilization","%",100);
  drawImpairSummary($("impairChart"),rows);
}

function renderRanking() {
  $("rfRankingBody").innerHTML=ranking.map((r,i)=>`
    <tr data-i="${i}">
      <td>${i+1}</td><td><strong>${esc(nd(r.nodo))}</strong></td><td>${esc(nd(r.cmts))}</td>
      <td>${esc(nd(r.upstream))}</td><td>${n1(r.cnr)}</td><td>${n1(r.signal_quality)}</td>
      <td>${n2(r.fec_pct)}</td><td>${n2(r.ufec_pct)}</td><td>${n1(r.utilization)}</td>
      <td>${Number(r.impair||0)===1?'<span class="rf-pill bad">ACTIVO</span>':'<span class="rf-pill ok">NO</span>'}</td>
      <td>${n1(r.score)}</td><td>${esc(nd(r.analytics_state))}</td>
    </tr>
  `).join("");
  $("rfRankingBody").querySelectorAll("tr[data-i]").forEach(tr=>tr.onclick=()=>selectRanking(Number(tr.dataset.i)));
}

function selectRanking(i) {
  selected=ranking[i]||null;
  if(!selected)return;
  $("rfSelected").textContent=`${selected.nodo} · ${selected.cmts} · ${selected.upstream}`;
  $("rfNode").value=selected.nodo||"";
  $("rfCmts").value=selected.cmts||"";
  $("rfUpstream").value=selected.upstream||"";
  updateSelectionStrip(selected);
  renderCharts([selected]);
  selectSpectrumForCurrentNode();
}

function groupSpectrumByNode(items) {
  spectrumGroups=new Map();
  items.forEach(x=>{
    const key=`${x.cmts||""}|${x.nodo||""}`;
    if(!spectrumGroups.has(key)) spectrumGroups.set(key,[]);
    spectrumGroups.get(key).push(x);
  });
}

function ensureSpectrumSelector() {
  if ($("rfSpectrumSelect")) return;
  const status=$("spectrumStatus");
  if(!status)return;

  const wrap=document.createElement("div");
  wrap.className="rf-spectrum-toolbar";
  wrap.innerHTML=`
    <div class="rf-spectrum-selectrow">
      <label><span>Nodo con Spectrum</span><select id="rfSpectrumSelect"></select></label>
      <span id="rfSpectrumCoverage"></span>
    </div>
    <div class="rf-spectrum-modes">
      <button type="button" class="rf-spectrum-mode active" data-mode="actual">Actual</button>
      <button type="button" class="rf-spectrum-mode" data-mode="max">Max Hold</button>
      <button type="button" class="rf-spectrum-mode" data-mode="avg">Promedio</button>
      <button type="button" class="rf-spectrum-mode" data-mode="waterfall">Waterfall</button>
      <span id="rfSpectrumMeta"></span>
    </div>
  `;
  status.insertAdjacentElement("afterend",wrap);
  $("rfSpectrumSelect").onchange=drawSelectedSpectrumNode;

  wrap.querySelectorAll(".rf-spectrum-mode").forEach(btn=>{
    btn.onclick=()=>{
      spectrumMode=btn.dataset.mode;
      wrap.querySelectorAll(".rf-spectrum-mode").forEach(x=>x.classList.toggle("active",x===btn));
      drawSelectedSpectrumNode();
    };
  });
}

function refreshSpectrumSelector() {
  ensureSpectrumSelector();
  const select=$("rfSpectrumSelect");
  const keys=[...spectrumGroups.keys()].sort((a,b)=>a.localeCompare(b,"es"));

  select.innerHTML=keys.map(k=>{
    const [cmts,nodo]=k.split("|");
    const rows=spectrumGroups.get(k)||[];
    const upstreams=[...new Set(rows.map(x=>x.upstream).filter(Boolean))];
    return `<option value="${esc(k)}">${esc(`${nodo} · ${cmts} · ${upstreams.length} upstreams`)}</option>`;
  }).join("");

  $("rfSpectrumCoverage").textContent=`${keys.length} nodos con Spectrum disponible`;
}

function latestNodeCapture(points) {
  if(!points.length)return [];
  const timestamps=[...new Set(points.map(x=>x.timestamp).filter(Boolean))].sort();
  const latest=timestamps[timestamps.length-1];
  return latest ? points.filter(x=>x.timestamp===latest) : points;
}

// HFC_SPECTRUM_HIGHRES_V22
function spectrumCaptures(points) {
  const byTs=new Map();
  points.forEach(p=>{
    const ts=p.timestamp || p.sample_time || p.captured_at || p.fecha || "";
    if(!ts)return;
    const key=String(ts);
    if(!byTs.has(key))byTs.set(key,[]);
    byTs.get(key).push(p);
  });
  return [...byTs.entries()]
    .sort((a,b)=>String(a[0]).localeCompare(String(b[0])))
    .map(([ts,pts])=>[
      ts,
      pts
        .filter(p=>Number.isFinite(Number(p.frequency_hz)) && Number.isFinite(Number(p.noise_dbmv)))
        .sort((a,b)=>Number(a.frequency_hz)-Number(b.frequency_hz))
    ]);
}

function aggregateFreq(points, op="max") {
  const map=new Map();
  points.forEach(p=>{
    const f=Number(p.frequency_hz), y=Number(p.noise_dbmv);
    if(!Number.isFinite(f)||!Number.isFinite(y))return;
    if(!map.has(f))map.set(f,[]);
    map.get(f).push(y);
  });
  return [...map.entries()].sort((a,b)=>a[0]-b[0]).map(([f,vals])=>({
    fMHz:f/1e6,
    value:op==="avg" ? vals.reduce((a,b)=>a+b,0)/vals.length : Math.max(...vals),
    min:Math.min(...vals),
    max:Math.max(...vals),
    count:vals.length
  }));
}

function spectrumScale(allValues) {
  let ymin=Math.min(...allValues), ymax=Math.max(...allValues);
  ymin=Math.min(-60,Math.floor((ymin-3)/10)*10);
  ymax=Math.max(20,Math.ceil((ymax+3)/10)*10);
  return {ymin,ymax};
}

function drawAnalyzerGrid(ctx,w,h,xmin,xmax,ymin,ymax,pad) {
  const X=x=>pad.l+(x-xmin)/(xmax-xmin)*(w-pad.l-pad.r);
  const Y=y=>pad.t+(1-(y-ymin)/(ymax-ymin))*(h-pad.t-pad.b);

  ctx.fillStyle="#101820";ctx.fillRect(0,0,w,h);
  ctx.font="10px Segoe UI";ctx.strokeStyle="#293845";ctx.lineWidth=1;ctx.fillStyle="#a9b7c4";

  for(let i=0;i<=9;i++){
    const x=pad.l+i*(w-pad.l-pad.r)/9;
    const f=xmin+i*(xmax-xmin)/9;
    ctx.beginPath();ctx.moveTo(x,pad.t);ctx.lineTo(x,h-pad.b);ctx.stroke();
    ctx.fillText(f.toFixed(1),x-10,h-15);
  }
  for(let i=0;i<=8;i++){
    const y=pad.t+i*(h-pad.t-pad.b)/8;
    const v=ymax-i*(ymax-ymin)/8;
    ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(w-pad.r,y);ctx.stroke();
    ctx.fillText(v.toFixed(0),12,y+4);
  }

  ctx.fillStyle="#d7e0e7";ctx.font="11px Segoe UI";
  ctx.fillText("Frecuencia (MHz)",w/2-42,h-4);
  ctx.save();ctx.translate(15,h/2+42);ctx.rotate(-Math.PI/2);ctx.fillText("Nivel de ruido (dBmV)",0,0);ctx.restore();
  return {X,Y};
}

function drawSpectrumBars(ctx,data,X,Y,ymin,pad,h,barColor="#25d3b2") {
  if(!data.length)return;
  const pts=data
    .filter(x=>Number.isFinite(Number(x.fMHz)) && Number.isFinite(Number(x.value)))
    .sort((a,b)=>Number(a.fMHz)-Number(b.fMHz));
  if(!pts.length)return;

  ctx.save();
  ctx.beginPath();
  ctx.moveTo(X(Number(pts[0].fMHz)),Y(ymin));
  pts.forEach((p,i)=>{
    const x=X(Number(p.fMHz));
    const y=Y(Number(p.value));
    if(i===0)ctx.lineTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.lineTo(X(Number(pts[pts.length-1].fMHz)),Y(ymin));
  ctx.closePath();

  const grad=ctx.createLinearGradient(0,pad.t,0,h-pad.b);
  grad.addColorStop(0,"rgba(37,211,178,.30)");
  grad.addColorStop(1,"rgba(37,211,178,.04)");
  ctx.fillStyle=grad;
  ctx.fill();

  ctx.beginPath();
  pts.forEach((p,i)=>{
    const x=X(Number(p.fMHz));
    const y=Y(Number(p.value));
    if(i===0)ctx.moveTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.strokeStyle=barColor;
  ctx.lineWidth=1.6;
  ctx.stroke();
  ctx.restore();
}

function drawSpectrumWaterfall(ctx,w,h,captures,pad) {
  const usable=captures.slice(-40);
  const freqs=[...new Set(
    usable.flatMap(([,pts])=>pts.map(p=>Number(p.frequency_hz)).filter(Number.isFinite))
  )].sort((a,b)=>a-b);

  if(!usable.length || !freqs.length){
    ctx.fillStyle="#9aa7b2";
    ctx.font="13px Segoe UI";
    ctx.fillText("Sin datos suficientes para Waterfall.",22,34);
    return;
  }

  const left=70,right=18,top=28,bottom=42;
  const gw=w-left-right;
  const gh=h-top-bottom;
  const values=usable.flatMap(([,pts])=>pts.map(p=>Number(p.noise_dbmv)).filter(Number.isFinite));
  const min=Math.min(...values), max=Math.max(...values);
  const range=Math.max(1,max-min);
  const rowH=gh/usable.length;
  const colW=gw/freqs.length;

  usable.forEach(([,pts],ri)=>{
    const rowMap=new Map(pts.map(p=>[Number(p.frequency_hz),Number(p.noise_dbmv)]));
    freqs.forEach((f,ci)=>{
      const v=rowMap.get(f);
      if(!Number.isFinite(v))return;
      const t=Math.max(0,Math.min(1,(v-min)/range));
      const hue=220-(220*t);
      const light=22+(38*t);
      ctx.fillStyle=`hsl(${hue} 90% ${light}%)`;
      ctx.fillRect(left+ci*colW,top+ri*rowH,Math.ceil(colW)+0.4,Math.ceil(rowH)+0.4);
    });
  });

  ctx.strokeStyle="rgba(255,255,255,.22)";
  ctx.strokeRect(left,top,gw,gh);
  ctx.fillStyle="#cbd5df";
  ctx.font="11px Segoe UI";
  ctx.fillText(`${(freqs[0]/1e6).toFixed(1)} MHz`,left,h-14);
  ctx.fillText(`${(freqs[freqs.length-1]/1e6).toFixed(1)} MHz`,w-right-58,h-14);
  ctx.fillText(`${usable.length} capturas`,left,16);
}

function drawSpectrumNode(points) {
  const canvas=$("spectrumChart");
  const {ctx,w,h}=prepCanvas(canvas,spectrumMode==="waterfall"?430:390);
  const captures=spectrumCaptures(points);
  const latest=captures.length?captures[captures.length-1][1]:[];

  const allValid=points.filter(x=>
    Number.isFinite(Number(x.frequency_hz)) &&
    Number.isFinite(Number(x.noise_dbmv))
  );

  const meta=$("rfSpectrumMeta");
  const widths=[...new Set(allValid.map(x=>Number(x.channel_width_hz)).filter(Number.isFinite))];
  const highres=allValid.filter(x=>Number(x.channel_width_hz)===200000);
  const distinctFreq=[...new Set(allValid.map(x=>Number(x.frequency_hz)).filter(Number.isFinite))];

  if(!allValid.length){
    ctx.fillStyle="#9aa7b2";
    ctx.font="13px Segoe UI";
    ctx.fillText("Sin datos Spectrum para este nodo.",22,34);
    if(meta)meta.textContent="Sin datos";
    return;
  }

  if(spectrumMode==="waterfall"){
    drawSpectrumWaterfall(ctx,w,h,captures,{});
    if(meta)meta.textContent=`${captures.length} capturas - ${distinctFreq.length} frecuencias - ${highres.length?"200 kHz":"legacy"}`;
    return;
  }

  const allValues=allValid.map(x=>Number(x.noise_dbmv)).filter(Number.isFinite);
  const {ymin,ymax}=spectrumScale(allValues);
  const minHz=Math.min(...distinctFreq);
  const maxHz=Math.max(...distinctFreq);
  const xmin=minHz/1e6;
  const xmax=maxHz/1e6;

  const pad={l:64,r:24,t:28,b:48};
  const {X,Y}=drawAnalyzerGrid(ctx,w,h,xmin,xmax,ymin,ymax,pad);

  let data=[],label="";
  if(spectrumMode==="actual"){
    data=aggregateFreq(latest,"max");
    label="Captura actual";
  }else if(spectrumMode==="max"){
    data=aggregateFreq(allValid,"max");
    label="Max Hold historico";
  }else{
    data=aggregateFreq(allValid,"avg");
    label="Promedio historico";
  }

  const color=spectrumMode==="avg"?"#58a6ff":"#25d3b2";
  drawSpectrumBars(ctx,data,X,Y,ymin,pad,h,color);
  ctx.fillStyle="#d7e0e7";
  ctx.font="600 11px Segoe UI";
  ctx.fillText(label,pad.l+8,pad.t+18);

  if(meta){
    const latestFreqs=new Set(latest.map(x=>Number(x.frequency_hz)).filter(Number.isFinite));
    const res=widths.includes(200000)?"200 kHz":(widths.length?`${Math.min(...widths)/1000} kHz`:"N/D");
    meta.textContent=`${captures.length} capturas - ${latestFreqs.size||distinctFreq.length} bins - resolucion ${res}`;
  }
}

function drawSelectedSpectrumNode() {
  const key=$("rfSpectrumSelect")?.value;
  drawSpectrumNode(key ? (spectrumGroups.get(key)||[]) : []);
}

function selectSpectrumForCurrentNode() {
  ensureSpectrumSelector();

  if(!selected){
    drawSelectedSpectrumNode();
    return;
  }

  const key=`${selected.cmts||""}|${selected.nodo||""}`;

  if(spectrumGroups.has(key)){
    $("rfSpectrumSelect").value=key;
    drawSelectedSpectrumNode();
  } else {
    $("spectrumStatus").textContent=`El nodo ${selected.nodo} no tiene captura Spectrum. Seleccione un nodo con Spectrum disponible.`;
    drawSelectedSpectrumNode();
  }
}

async function loadSpectrumIndex() {
  try{
    const s=await get("spectrum",{limit:20000});
    groupSpectrumByNode(s.items||[]);
    refreshSpectrumSelector();
    drawSelectedSpectrumNode();
  }catch(e){
    $("spectrumStatus").textContent="Error Spectrum: "+e.message;
  }
}

async function searchUpstreams() {
  const p={limit:200,offset:0};
  const node=$("rfNode").value.trim();
  const cmts=$("rfCmts").value.trim();
  const up=$("rfUpstream").value.trim();
  const q=$("rfSearch").value.trim();

  if(node)p.node=node;
  if(cmts)p.cmts=cmts;
  if(up)p.upstream=up;
  if(q)p.search=q;

  $("rfSearchStatus").textContent="Consultando upstreams...";

  try{
    const u=await get("upstreams",p);
    const rows=u.items||[];

    $("rfSearchStatus").textContent=`${fmt(u.total||rows.length)} upstreams encontrados · mostrando ${fmt(rows.length)}`;

    selected=rows.length===1?rows[0]:null;
    updateSelectionStrip(selected);
    renderCharts(rows.slice(0,15));

    if(selected){
      $("rfSelected").textContent=`${selected.nodo} · ${selected.cmts} · ${selected.upstream}`;
      selectSpectrumForCurrentNode();
    }
  }catch(e){
    $("rfSearchStatus").textContent="Error: "+e.message;
  }
}

async function loadRf(force=false) {
  if(rfLoading || (summary&&!force))return;
  rfLoading=true;

  $("rfGlobalStatus").textContent="Cargando RF nacional...";

  try{
    const [s,r]=await Promise.all([
      get("resumen"),
      get("ranking",{limit:20})
    ]);

    summary=s;
    ranking=r.items||[];

    renderKpis();
    renderRanking();
    renderCharts(ranking);
    updateSelectionStrip(null);

    $("rfGlobalStatus").textContent=`RF actualizado · ${fmt(summary.upstreams_total)} upstreams · ${fmt(summary.spectrum_points)} puntos Spectrum`;

    await loadSpectrumIndex();
  }catch(e){
    $("rfGlobalStatus").textContent="Error RF: "+e.message;
  }finally{rfLoading=false;}
}

$("rfRefresh").onclick=()=>{summary=null;loadRf(true)};
$("rfApply").onclick=searchUpstreams;
$("rfSpectrum").onclick=selectSpectrumForCurrentNode;
$("rfClear").onclick=()=>{
  ["rfNode","rfCmts","rfUpstream","rfSearch"].forEach(id=>$(id).value="");
  selected=null;
  $("rfSelected").textContent="Selección nacional";
  updateSelectionStrip(null);
  renderCharts(ranking);
  drawSelectedSpectrumNode();
};

window.addEventListener("resize",()=>{
  if($("tabRf")?.classList.contains("active")){
    renderCharts(selected?[selected]:ranking);
    drawSelectedSpectrumNode();
  }
});


/* ================= HFC_SPECTRUM_NODE_SCOPE_V23 ================= */
let spectrumNodePointsV23=[];
let spectrumUpstreamV23="__NODE__";

function spectrumFieldV23(p,name){
  if(name==="node") return p.nodo ?? p.node ?? "";
  if(name==="timestamp") return p.timestamp ?? p.sample_time ?? p.captured_at ?? "";
  return p[name];
}

function spectrumScopePointsV23(){
  if(spectrumUpstreamV23==="__NODE__") return spectrumNodePointsV23;
  return spectrumNodePointsV23.filter(p=>String(p.upstream||"")===String(spectrumUpstreamV23));
}

function spectrumEnvelopeV23(points,mode="max"){
  const byFreq=new Map();
  points.forEach(p=>{
    const f=Number(p.frequency_hz);
    const v=Number(p.noise_dbmv);
    if(!Number.isFinite(f)||!Number.isFinite(v))return;
    if(!byFreq.has(f))byFreq.set(f,[]);
    byFreq.get(f).push(v);
  });
  return [...byFreq.entries()]
    .sort((a,b)=>a[0]-b[0])
    .map(([f,vals])=>({
      fMHz:f/1e6,
      value:mode==="avg"
        ? vals.reduce((a,b)=>a+b,0)/vals.length
        : Math.max(...vals)
    }));
}

function spectrumCapturesV23(points){
  const byTs=new Map();
  points.forEach(p=>{
    const ts=spectrumFieldV23(p,"timestamp");
    if(!ts)return;
    if(!byTs.has(ts))byTs.set(ts,[]);
    byTs.get(ts).push(p);
  });
  return [...byTs.entries()].sort((a,b)=>String(a[0]).localeCompare(String(b[0])));
}

function spectrumScaleV23(values){
  const vals=values.filter(Number.isFinite);
  if(!vals.length)return {ymin:-40,ymax:10};
  const lo=Math.min(...vals),hi=Math.max(...vals);
  let ymin=Math.floor((lo-3)/5)*5;
  let ymax=Math.ceil((hi+3)/5)*5;
  ymin=Math.min(ymin,-30);
  ymax=Math.max(ymax,5);
  if((ymax-ymin)<25)ymin=ymax-25;
  return {ymin,ymax};
}

function drawTraceV23(ctx,data,X,Y,stroke,width=1.2,alpha=1){
  if(!data.length)return;
  ctx.save();
  ctx.globalAlpha=alpha;
  ctx.beginPath();
  data.forEach((p,i)=>{
    const x=X(Number(p.fMHz)),y=Y(Number(p.value));
    if(i===0)ctx.moveTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.strokeStyle=stroke;
  ctx.lineWidth=width;
  ctx.stroke();
  ctx.restore();
}

function drawNodeActualV23(ctx,latest,X,Y){
  const byUs=new Map();
  latest.forEach(p=>{
    const us=String(p.upstream||"N/D");
    if(!byUs.has(us))byUs.set(us,[]);
    byUs.get(us).push(p);
  });

  [...byUs.values()].forEach(pts=>{
    drawTraceV23(ctx,spectrumEnvelopeV23(pts,"max"),X,Y,"#6f8798",0.9,0.42);
  });

  drawTraceV23(ctx,spectrumEnvelopeV23(latest,"max"),X,Y,"#21d4b4",2.0,1);
}

function nodeCaptureEnvelopesV23(captures){
  return captures.map(([ts,pts])=>[
    ts,
    spectrumEnvelopeV23(pts,"max").map(p=>({
      frequency_hz:p.fMHz*1e6,
      noise_dbmv:p.value
    }))
  ]);
}

function ensureSpectrumUpstreamV23(){
  const toolbar=document.querySelector(".rf-spectrum-toolbar");
  if(!toolbar)return;

  let group=$("rfSpectrumUpstreamGroup");
  if(!group){
    group=document.createElement("div");
    group.id="rfSpectrumUpstreamGroup";
    group.className="rf-spectrum-upstream-group";
    group.innerHTML=`
      <span class="rf-spectrum-mini-label">VISTA</span>
      <select id="rfSpectrumUpstream"></select>
    `;
    const nodeSelect=$("rfSpectrumSelect");
    if(nodeSelect && nodeSelect.parentElement===toolbar){
      nodeSelect.insertAdjacentElement("afterend",group);
    }else{
      toolbar.prepend(group);
    }
  }

  const sel=$("rfSpectrumUpstream");
  if(sel && !sel.dataset.boundV23){
    sel.dataset.boundV23="1";
    sel.onchange=()=>{
      spectrumUpstreamV23=sel.value||"__NODE__";
      drawSelectedSpectrumNode();
    };
  }
}

function refreshUpstreamSelectorV23(){
  ensureSpectrumUpstreamV23();
  const sel=$("rfSpectrumUpstream");
  if(!sel)return;

  const upstreams=[...new Set(
    spectrumNodePointsV23.map(p=>String(p.upstream||"")).filter(Boolean)
  )].sort((a,b)=>a.localeCompare(b,"es"));

  const current=spectrumUpstreamV23;
  sel.innerHTML=[
    `<option value="__NODE__">Nodo completo (${upstreams.length} upstreams)</option>`,
    ...upstreams.map(us=>`<option value="${esc(us)}">Upstream ${esc(us)}</option>`)
  ].join("");

  if(current!=="__NODE__" && upstreams.includes(current)){
    sel.value=current;
  }else{
    spectrumUpstreamV23="__NODE__";
    sel.value="__NODE__";
  }
}

async function loadSelectedSpectrumNodeV23(){
  const key=$("rfSpectrumSelect")?.value;
  if(!key){
    spectrumNodePointsV23=[];
    refreshUpstreamSelectorV23();
    drawSelectedSpectrumNode();
    return;
  }

  const [cmts,nodo]=String(key).split("|");
  const status=$("spectrumStatus");
  if(status)status.textContent=`Cargando Spectrum completo de ${nodo}...`;

  try{
    const s=await get("spectrum",{cmts,node:nodo,limit:20000});
    spectrumNodePointsV23=(s.items||[]).filter(p=>{
      const pn=String(spectrumFieldV23(p,"node"));
      return (!nodo || pn===String(nodo)) && (!cmts || String(p.cmts||"")===String(cmts));
    });

    refreshUpstreamSelectorV23();
    drawSelectedSpectrumNode();

    const usCount=new Set(spectrumNodePointsV23.map(p=>p.upstream).filter(Boolean)).size;
    const highBins=new Set(
      spectrumNodePointsV23
        .filter(p=>Number(p.channel_width_hz)===200000)
        .map(p=>Number(p.frequency_hz))
        .filter(Number.isFinite)
    ).size;

    if(status){
      status.textContent=`Nodo ${nodo}: ${usCount} upstreams - ${highBins||"N/D"} bins high-res disponibles`;
    }
  }catch(e){
    spectrumNodePointsV23=[];
    if(status)status.textContent="Error Spectrum nodo: "+e.message;
    drawSelectedSpectrumNode();
  }
}

function drawSpectrumNode(points) {
  const canvas=$("spectrumChart");
  const {ctx,w,h}=prepCanvas(canvas,spectrumMode==="waterfall"?430:410);

  const valid=spectrumScopePointsV23().filter(p=>
    Number.isFinite(Number(p.frequency_hz)) &&
    Number.isFinite(Number(p.noise_dbmv))
  );

  const meta=$("rfSpectrumMeta");

  if(!valid.length){
    ctx.fillStyle="#94a3b8";
    ctx.font="13px Segoe UI";
    ctx.fillText("Sin datos Spectrum para esta selección.",24,38);
    if(meta)meta.textContent="Sin datos";
    return;
  }

  const captures=spectrumCapturesV23(valid);
  const latest=captures.length?captures[captures.length-1][1]:[];
  const freqs=[...new Set(valid.map(p=>Number(p.frequency_hz)).filter(Number.isFinite))].sort((a,b)=>a-b);
  const upstreams=[...new Set(valid.map(p=>String(p.upstream||"")).filter(Boolean))];

  if(spectrumMode==="waterfall"){
    const wf=spectrumUpstreamV23==="__NODE__" ? nodeCaptureEnvelopesV23(captures) : captures;
    drawSpectrumWaterfall(ctx,w,h,wf,{});
    if(meta){
      meta.textContent=spectrumUpstreamV23==="__NODE__"
        ? `Nodo completo - ${upstreams.length} upstreams - ${captures.length} capturas - envolvente por frecuencia`
        : `Upstream ${spectrumUpstreamV23} - ${captures.length} capturas - ${freqs.length} bins`;
    }
    return;
  }

  const values=valid.map(p=>Number(p.noise_dbmv)).filter(Number.isFinite);
  const {ymin,ymax}=spectrumScaleV23(values);
  const xmin=Math.min(...freqs)/1e6;
  const xmax=Math.max(...freqs)/1e6;
  const pad={l:66,r:22,t:30,b:48};
  const {X,Y}=drawAnalyzerGrid(ctx,w,h,xmin,xmax,ymin,ymax,pad);

  if(spectrumMode==="actual"){
    if(spectrumUpstreamV23==="__NODE__"){
      drawNodeActualV23(ctx,latest,X,Y);
    }else{
      drawTraceV23(ctx,spectrumEnvelopeV23(latest,"max"),X,Y,"#21d4b4",2.0,1);
    }
  }else if(spectrumMode==="max"){
    drawTraceV23(ctx,spectrumEnvelopeV23(valid,"max"),X,Y,"#f6c85f",2.0,1);
  }else{
    drawTraceV23(ctx,spectrumEnvelopeV23(valid,"avg"),X,Y,"#58a6ff",2.0,1);
  }

  ctx.fillStyle="#dce6ee";
  ctx.font="600 11px Segoe UI";
  const title=spectrumMode==="actual"
    ? (spectrumUpstreamV23==="__NODE__"?"Nodo completo - envolvente actual":"Upstream "+spectrumUpstreamV23+" - actual")
    : spectrumMode==="max" ? "Max Hold historico" : "Promedio historico";
  ctx.fillText(title,pad.l+8,pad.t+17);

  if(meta){
    const latestBins=new Set(latest.map(p=>Number(p.frequency_hz)).filter(Number.isFinite)).size;
    meta.textContent=spectrumUpstreamV23==="__NODE__"
      ? `Nodo completo - ${upstreams.length} upstreams - ${latestBins} bins - 200 kHz`
      : `Upstream ${spectrumUpstreamV23} - ${latestBins} bins - 200 kHz`;
  }
}

function drawSelectedSpectrumNode(){
  drawSpectrumNode(spectrumNodePointsV23);
}

function refreshSpectrumSelector(){
  ensureSpectrumSelector();
  ensureSpectrumUpstreamV23();

  const select=$("rfSpectrumSelect");
  const keys=[...spectrumGroups.keys()].sort((a,b)=>a.localeCompare(b,"es"));
  const old=select.value;

  select.innerHTML=keys.map(k=>{
    const [cmts,nodo]=k.split("|");
    const pts=spectrumGroups.get(k)||[];
    const us=new Set(pts.map(x=>x.upstream).filter(Boolean)).size;
    return `<option value="${esc(k)}">${esc(nodo)} - ${esc(cmts)} - ${us} upstreams</option>`;
  }).join("");

  if(old && keys.includes(old))select.value=old;
  else if(keys.length)select.value=keys[0];

  if(!select.dataset.boundV23){
    select.dataset.boundV23="1";
    select.onchange=async()=>{
      spectrumUpstreamV23="__NODE__";
      await loadSelectedSpectrumNodeV23();
    };
  }
}

async function loadSpectrumIndex(){
  try{
    const s=await get("spectrum",{limit:20000});
    groupSpectrumByNode(s.items||[]);
    refreshSpectrumSelector();
    await loadSelectedSpectrumNodeV23();
  }catch(e){
    const st=$("spectrumStatus");
    if(st)st.textContent="Error Spectrum: "+e.message;
  }
}

function selectSpectrumForCurrentNode(){
  ensureSpectrumSelector();
  if(!selected){
    drawSelectedSpectrumNode();
    return;
  }

  const key=`${selected.cmts||""}|${selected.nodo||selected.node||""}`;
  const select=$("rfSpectrumSelect");

  if(spectrumGroups.has(key) && select){
    select.value=key;
    spectrumUpstreamV23="__NODE__";
    loadSelectedSpectrumNodeV23();
  }else{
    drawSelectedSpectrumNode();
  }
}
/* ================= /HFC_SPECTRUM_NODE_SCOPE_V23 ================= */

/* =========================================================================================
   DASHBOARD HFC RF - NOC VISUAL OVERLAY V1
   Solo visual: conserva contratos, endpoints, filtros y datos existentes.
   ========================================================================================= */

function rfNocStateColor(row){
  const state=String(row?.analytics_state||"").toUpperCase();
  if(state.includes("ALTA")||state.includes("CRIT")) return "#d92d20";
  if(state.includes("MEDIA")||state.includes("DEGRAD")) return "#f79009";
  if(state.includes("VIGIL")) return "#fdb022";
  if(state.includes("NORMAL")||state.includes("OK")) return "#12b76a";
  if(Number(row?.impair||0)===1) return "#d92d20";
  return "#2563eb";
}

function rfNocRoundedRect(ctx,x,y,w,h,r){
  const rr=Math.min(r,h/2,w/2);
  ctx.beginPath();
  ctx.moveTo(x+rr,y);
  ctx.arcTo(x+w,y,x+w,y+h,rr);
  ctx.arcTo(x+w,y+h,x,y+h,rr);
  ctx.arcTo(x,y+h,x,y,rr);
  ctx.arcTo(x,y,x+w,y,rr);
  ctx.closePath();
}

function rfNocMetricMeta(key){
  const map={
    cnr:{title:"CNR",unit:" dB",kind:"bullet",accent:"#2563eb"},
    signal_quality:{title:"Signal Quality",unit:" dB",kind:"bullet",accent:"#0ea5e9"},
    fec_pct:{title:"FEC",unit:"%",kind:"lollipop",accent:"#7c3aed"},
    ufec_pct:{title:"uFEC",unit:"%",kind:"lollipop",accent:"#dc2626"},
    utilization:{title:"Utilización",unit:"%",kind:"capacity",accent:"#f79009"}
  };
  return map[key]||{title:key,unit:"",kind:"bullet",accent:"#2563eb"};
}

function drawHorizontalMetric(canvas, rows, key, unit="", maxHint=null){
  const data=rows
    .filter(r=>Number.isFinite(Number(r[key])))
    .slice()
    .sort((a,b)=>{
      if(key==="cnr"||key==="signal_quality") return Number(a[key])-Number(b[key]);
      return Number(b[key])-Number(a[key]);
    })
    .slice(0,10);

  const {ctx,w,h}=prepCanvas(canvas,300);
  const meta=rfNocMetricMeta(key);

  ctx.save();
  ctx.clearRect(0,0,w,h);

  if(!data.length){
    ctx.fillStyle="#667085";
    ctx.font="500 12px Segoe UI";
    ctx.fillText("Sin datos disponibles",22,38);
    ctx.restore();
    return;
  }

  const values=data.map(r=>Number(r[key]));
  let max=Math.max(...values,1);
  if(maxHint!==null) max=Math.max(max,Number(maxHint)||0);

  const left=150,right=76,top=22,bottom=28;
  const plotW=Math.max(80,w-left-right);
  const rowH=(h-top-bottom)/data.length;

  // Header scale
  ctx.font="500 10px Segoe UI";
  ctx.fillStyle="#98a2b3";
  for(let i=0;i<=4;i++){
    const x=left+(plotW*i/4);
    const label=(max*i/4).toFixed(max>20?0:1);
    ctx.fillText(label,x-8,13);
    ctx.strokeStyle="rgba(152,162,179,.16)";
    ctx.lineWidth=1;
    ctx.beginPath();
    ctx.moveTo(x,top);
    ctx.lineTo(x,h-bottom);
    ctx.stroke();
  }

  data.forEach((r,i)=>{
    const v=Number(r[key]);
    const cy=top+i*rowH+rowH/2;
    const name=`${r.nodo||"—"} · ${r.upstream||"—"}`;
    const stateColor=rfNocStateColor(r);

    // row label
    ctx.fillStyle="#344054";
    ctx.font="600 11px Segoe UI";
    const label=name.length>22?name.slice(0,21)+"…":name;
    ctx.fillText(label,8,cy+4);

    if(meta.kind==="lollipop"){
      // baseline
      ctx.strokeStyle="#e4e7ec";
      ctx.lineWidth=5;
      ctx.lineCap="round";
      ctx.beginPath();
      ctx.moveTo(left,cy);
      ctx.lineTo(left+plotW,cy);
      ctx.stroke();

      const px=left+Math.max(0,Math.min(1,v/max))*plotW;
      ctx.strokeStyle=meta.accent;
      ctx.lineWidth=3;
      ctx.beginPath();
      ctx.moveTo(left,cy);
      ctx.lineTo(px,cy);
      ctx.stroke();

      ctx.fillStyle=stateColor;
      ctx.beginPath();
      ctx.arc(px,cy,6,0,Math.PI*2);
      ctx.fill();

      ctx.strokeStyle="#fff";
      ctx.lineWidth=2;
      ctx.stroke();
    }else{
      // technical bullet rail
      const railH=10;
      const y=cy-railH/2;

      ctx.fillStyle="#f2f4f7";
      rfNocRoundedRect(ctx,left,y,plotW,railH,6);
      ctx.fill();

      const bw=Math.max(3,Math.min(plotW,plotW*(v/max)));
      const grad=ctx.createLinearGradient(left,0,left+plotW,0);
      grad.addColorStop(0,meta.accent);
      grad.addColorStop(1,stateColor);
      ctx.fillStyle=grad;
      rfNocRoundedRect(ctx,left,y,bw,railH,6);
      ctx.fill();

      const px=left+bw;
      ctx.fillStyle="#fff";
      ctx.strokeStyle=stateColor;
      ctx.lineWidth=3;
      ctx.beginPath();
      ctx.arc(px,cy,5,0,Math.PI*2);
      ctx.fill();
      ctx.stroke();
    }

    // value pill
    const valueText=`${key.includes("fec")?v.toFixed(2):v.toFixed(1)}${unit||meta.unit}`;
    ctx.font="700 11px Segoe UI";
    const tw=ctx.measureText(valueText).width;
    ctx.fillStyle="#101828";
    ctx.fillText(valueText,w-right+18,cy+4);

    // status dot
    ctx.fillStyle=stateColor;
    ctx.beginPath();
    ctx.arc(w-14,cy,4,0,Math.PI*2);
    ctx.fill();
  });

  ctx.restore();
}

function drawImpairSummary(canvas, rows){
  const {ctx,w,h}=prepCanvas(canvas,300);
  const total=rows.length||1;
  const active=rows.filter(r=>Number(r.impair||0)===1).length;
  const inactive=Math.max(0,total-active);
  const pct=(active/total)*100;

  ctx.save();
  ctx.clearRect(0,0,w,h);

  const cx=Math.min(150,w*.31);
  const cy=145;
  const radius=Math.min(82,w*.18);
  const line=22;

  // ring background
  ctx.lineWidth=line;
  ctx.lineCap="round";
  ctx.strokeStyle="#eaecf0";
  ctx.beginPath();
  ctx.arc(cx,cy,radius,-Math.PI*.75,Math.PI*.75);
  ctx.stroke();

  // active arc
  const start=-Math.PI*.75;
  const sweep=Math.PI*1.5*(active/total);
  ctx.strokeStyle=active? "#d92d20":"#12b76a";
  ctx.beginPath();
  ctx.arc(cx,cy,radius,start,start+sweep);
  ctx.stroke();

  // center
  ctx.textAlign="center";
  ctx.fillStyle="#101828";
  ctx.font="800 32px Segoe UI";
  ctx.fillText(String(active),cx,cy+4);
  ctx.font="600 11px Segoe UI";
  ctx.fillStyle="#667085";
  ctx.fillText("IMPAIR ACTIVOS",cx,cy+26);

  ctx.font="700 12px Segoe UI";
  ctx.fillStyle=active?"#b42318":"#027a48";
  ctx.fillText(`${pct.toFixed(1)}%`,cx,cy+47);

  ctx.textAlign="left";
  const lx=Math.max(cx+radius+55,w*.56);
  const ly=86;

  const cards=[
    ["Activos",active,"#d92d20"],
    ["Sin impair",inactive,"#12b76a"],
    ["Total",total,"#2563eb"]
  ];

  cards.forEach(([label,value,color],i)=>{
    const y=ly+i*57;
    ctx.fillStyle=color;
    ctx.beginPath();ctx.arc(lx,y,5,0,Math.PI*2);ctx.fill();
    ctx.fillStyle="#667085";
    ctx.font="600 11px Segoe UI";
    ctx.fillText(label,lx+15,y+4);
    ctx.fillStyle="#101828";
    ctx.font="800 20px Segoe UI";
    ctx.fillText(String(value),lx+15,y+26);
  });

  ctx.restore();
}

function drawAnalyzerGrid(ctx,w,h,xmin,xmax,ymin,ymax,pad){
  // Fondo claro técnico; elimina negro puro
  const bg=ctx.createLinearGradient(0,pad.t,0,h-pad.b);
  bg.addColorStop(0,"#f8fbff");
  bg.addColorStop(1,"#eef4fa");
  ctx.fillStyle=bg;
  ctx.fillRect(pad.l,pad.t,w-pad.l-pad.r,h-pad.t-pad.b);

  const X=x=>pad.l+((x-xmin)/Math.max(.0001,xmax-xmin))*(w-pad.l-pad.r);
  const Y=y=>pad.t+(1-((y-ymin)/Math.max(.0001,ymax-ymin)))*(h-pad.t-pad.b);

  // vertical frequency grid
  ctx.font="500 10px Segoe UI";
  for(let i=0;i<=8;i++){
    const t=i/8;
    const x=pad.l+t*(w-pad.l-pad.r);
    const value=xmin+t*(xmax-xmin);

    ctx.strokeStyle="rgba(37,99,235,.10)";
    ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(x,pad.t);ctx.lineTo(x,h-pad.b);ctx.stroke();

    ctx.fillStyle="#667085";
    ctx.fillText(value.toFixed(1),x-12,h-pad.b+18);
  }

  // horizontal noise grid
  for(let i=0;i<=6;i++){
    const t=i/6;
    const y=pad.t+t*(h-pad.t-pad.b);
    const value=ymax-t*(ymax-ymin);

    ctx.strokeStyle="rgba(15,23,42,.09)";
    ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(w-pad.r,y);ctx.stroke();

    ctx.fillStyle="#667085";
    ctx.fillText(value.toFixed(0),10,y+4);
  }

  // plot border
  ctx.strokeStyle="#cbd5e1";
  ctx.lineWidth=1;
  ctx.strokeRect(pad.l,pad.t,w-pad.l-pad.r,h-pad.t-pad.b);

  ctx.fillStyle="#475467";
  ctx.font="600 10px Segoe UI";
  ctx.fillText("Frecuencia (MHz)",w/2-38,h-5);
  ctx.save();
  ctx.translate(14,h/2+36);
  ctx.rotate(-Math.PI/2);
  ctx.fillText("Nivel de ruido (dBmV)",0,0);
  ctx.restore();

  return {X,Y};
}

function drawSpectrumBars(ctx,data,X,Y,ymin,pad,h,barColor="#0ea5e9"){
  if(!data.length)return;

  const pts=data
    .filter(x=>Number.isFinite(Number(x.fMHz))&&Number.isFinite(Number(x.value)))
    .sort((a,b)=>Number(a.fMHz)-Number(b.fMHz));

  if(!pts.length)return;

  ctx.save();

  // area fill
  const grad=ctx.createLinearGradient(0,pad.t,0,h-pad.b);
  grad.addColorStop(0,"rgba(14,165,233,.28)");
  grad.addColorStop(1,"rgba(14,165,233,.025)");

  ctx.beginPath();
  ctx.moveTo(X(Number(pts[0].fMHz)),Y(ymin));
  pts.forEach(p=>ctx.lineTo(X(Number(p.fMHz)),Y(Number(p.value))));
  ctx.lineTo(X(Number(pts[pts.length-1].fMHz)),Y(ymin));
  ctx.closePath();
  ctx.fillStyle=grad;
  ctx.fill();

  // glow trace
  ctx.beginPath();
  pts.forEach((p,i)=>{
    const x=X(Number(p.fMHz)),y=Y(Number(p.value));
    if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
  });
  ctx.strokeStyle="rgba(14,165,233,.22)";
  ctx.lineWidth=6;
  ctx.stroke();

  ctx.beginPath();
  pts.forEach((p,i)=>{
    const x=X(Number(p.fMHz)),y=Y(Number(p.value));
    if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
  });
  ctx.strokeStyle=barColor==="#25d3b2"?"#0ea5e9":barColor;
  ctx.lineWidth=2.2;
  ctx.stroke();

  ctx.restore();
}

function renderRanking(){
  $("rfRankingBody").innerHTML=ranking.map((r,i)=>{
    const state=String(nd(r.analytics_state));
    const stateUpper=state.toUpperCase();
    const stateClass=(stateUpper.includes("ALTA")||stateUpper.includes("CRIT"))
      ?"critical"
      :(stateUpper.includes("MEDIA")||stateUpper.includes("DEGRAD"))
        ?"warning"
        :(stateUpper.includes("NORMAL")||stateUpper.includes("OK"))
          ?"ok":"neutral";

    const score=Number(r.score);
    const scoreSafe=Number.isFinite(score)?Math.max(0,Math.min(100,score)):0;

    return `
      <tr data-i="${i}">
        <td><span class="rf-rank-num">${i+1}</span></td>
        <td><strong class="rf-node-name">${esc(nd(r.nodo))}</strong></td>
        <td class="rf-cmts-cell">${esc(nd(r.cmts))}</td>
        <td><span class="rf-upstream-chip">${esc(nd(r.upstream))}</span></td>
        <td>${n1(r.cnr)}</td>
        <td>${n1(r.signal_quality)}</td>
        <td>${n2(r.fec_pct)}</td>
        <td>${n2(r.ufec_pct)}</td>
        <td>${n1(r.utilization)}</td>
        <td>${Number(r.impair||0)===1
          ?'<span class="rf-pill bad">● ACTIVO</span>'
          :'<span class="rf-pill ok">● NO</span>'}
        </td>
        <td>
          <div class="rf-score-cell">
            <strong>${n1(r.score)}</strong>
            <span class="rf-score-track"><i style="width:${scoreSafe}%"></i></span>
          </div>
        </td>
        <td><span class="rf-state-pill ${stateClass}">${esc(state)}</span></td>
      </tr>
    `;
  }).join("");

  $("rfRankingBody").querySelectorAll("tr[data-i]")
    .forEach(tr=>tr.onclick=()=>selectRanking(Number(tr.dataset.i)));
}

})();

(() => {
  'use strict';
  const CFG = window.HFC_NODE_CARD_CONFIG || {};
  const endpoint = CFG.analyticsNodesUrl || '';
  if (!endpoint) { console.warn('[HFC Node Card] analyticsNodesUrl no configurado'); return; }

  const q = (s, r=document) => r.querySelector(s);
  const qa = (s, r=document) => Array.from(r.querySelectorAll(s));
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const fmt = (v, suffix='') => {
    if (v === null || v === undefined || v === '' || String(v).toUpperCase() === 'NONE') return 'N/D';
    return esc(v) + suffix;
  };
  const boolText = (v) => v === true || String(v).toLowerCase()==='true' ? 'Sí' : (v === false || String(v).toLowerCase()==='false' ? 'No' : 'N/D');

  function section(title, body, cls='') {
    return `<section class="hfc-node-card__section ${cls}"><div class="hfc-node-card__section-title">${esc(title)}</div><div class="hfc-node-card__grid">${body}</div></section>`;
  }
  function item(label, value, cls='') {
    return `<div class="hfc-node-card__item ${cls}"><span class="hfc-node-card__label">${esc(label)}</span><strong class="hfc-node-card__value">${value}</strong></div>`;
  }
  function stateClass(v) {
    const s = String(v || '').toUpperCase();
    if (s.includes('ALTA')) return 'is-critical';
    if (s.includes('AFECTACION')) return 'is-major';
    if (s.includes('OBSERVACION')) return 'is-warning';
    if (s.includes('SIN_DATOS')) return 'is-muted';
    return 'is-ok';
  }

  function ensureDrawer() {
    let root = q('#hfc-node-card-drawer');
    if (root) return root;
    root = document.createElement('div');
    root.id = 'hfc-node-card-drawer';
    root.className = 'hfc-node-card';
    root.innerHTML = `
      <div class="hfc-node-card__backdrop" data-close="1"></div>
      <aside class="hfc-node-card__panel" role="dialog" aria-modal="true" aria-label="Ficha operativa HFC">
        <header class="hfc-node-card__header">
          <div>
            <div class="hfc-node-card__eyebrow">Ficha operativa HFC</div>
            <h2 id="hfc-node-card-title">Nodo</h2>
            <div id="hfc-node-card-subtitle" class="hfc-node-card__subtitle"></div>
          </div>
          <button class="hfc-node-card__close" type="button" data-close="1" aria-label="Cerrar">×</button>
        </header>
        <div id="hfc-node-card-body" class="hfc-node-card__body"><div class="hfc-node-card__loading">Selecciona un nodo para ver el detalle.</div></div>
      </aside>`;
    document.body.appendChild(root);
    root.addEventListener('click', e => { if (e.target && e.target.closest('[data-close="1"]')) closeDrawer(); });
    root.addEventListener('keydown',e=>{if(e.key==='Tab'){const focusable=qa('button,a[href],input,select,[tabindex="0"]',root).filter(el=>!el.disabled);const first=focusable[0],last=focusable[focusable.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}});
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && root.classList.contains('is-open')) closeDrawer(); });
    return root;
  }
  let returnFocus=null;
  function openDrawer() {
    ensureDrawer().classList.add('is-open');
    document.documentElement.classList.add('hfc-node-card-open');
    q('.main').inert=true;q('#main-sidebar').inert=true;
    q('.hfc-node-card__close').focus();
  }
  function closeDrawer() {
    const root = q('#hfc-node-card-drawer');
    if (root) root.classList.remove('is-open');
    document.documentElement.classList.remove('hfc-node-card-open');
    q('.main').inert=false;q('#main-sidebar').inert=false;
    if(returnFocus?.isConnected)returnFocus.focus();
    document.querySelectorAll('tr.is-selected').forEach(row=>row.classList.remove('is-selected'));
  }

  function renderNode(d) {
    const root = ensureDrawer();
    q('#hfc-node-card-title', root).textContent = d.nodo || 'Nodo';
    q('#hfc-node-card-subtitle', root).textContent = [d.cmts, d.tecnologia, d.regional || 'N/D'].filter(Boolean).join(' · ');

    q('#hfc-node-card-body', root).innerHTML = [
      section('Identificación', [
        item('Nodo', fmt(d.nodo)), item('CMTS', fmt(d.cmts)), item('Tecnología', fmt(d.tecnologia)),
        item('Zona', fmt(d.zona)), item('Regional', fmt(d.regional))
      ].join('')),
      section('Estado operativo', [
        item('Estado V5', `<span class="hfc-node-card__state ${stateClass(d.estado)}">${fmt(d.estado)}</span>`),
        item('Estado desde', fmt(d.estado_desde)), item('Días en estado', fmt(d.dias_estado)),
        item('Sumatoria', fmt(d.sumatoria)), item('Exclusión', fmt(d.exclusion)),
        item('Tipo exclusión', fmt(d.exclusion_types)), item('Motivo exclusión', fmt(d.exclusion_reasons), 'span-2')
      ].join('')),
      section('Impacto', [
        item('Hogares', fmt(d.hogares)), item('Activos', fmt(d.active_oper)), item('Registrados', fmt(d.registered)),
        item('Offline', fmt(d.offline)), item('% Offline', fmt(d.porc_offline, '%'))
      ].join('')),
      section('RF / Calidad', [
        item('% PL', fmt(d.pl_pct, '%')), item('% FEC', fmt(d.fec_pct, '%')), item('% uFEC', fmt(d.ufec_pct, '%')),
        item('% QPSK', fmt(d.qpsk_pct, '%')), item('SNR UP', fmt(d.snr_up)), item('SQ', fmt(d.signal_quality)),
        item('QOE', fmt(d.qoe)), item('Utilización máx.', fmt(d.utilization_max)), item('Impair', fmt(d.impair))
      ].join('')),
      section('Diagnóstico', [
        item('Upstream principal', fmt(d.main_upstream)), item('Diagnóstico principal', fmt(d.main_diagnosis), 'span-2')
      ].join('')),
      section('Incidencia operativa', [
        item('INC', fmt(d.incident)), item('Estado INC', fmt(d.incident_status)), item('Apertura INC', fmt(d.incident_opened_at)),
        item('TAS', fmt(d.tas)), item('Estado TAS', fmt(d.tas_status)), item('Apertura TAS', fmt(d.tas_opened_at)),
        item('OT', fmt(d.ot)), item('Estado OT', fmt(d.ot_status)), item('Apertura OT', fmt(d.ot_opened_at)),
        item('Días TK abierto', fmt(d.dias_tk_abierto)), item('Incidentes relacionados', fmt(d.incidentes_relacionados)),
        item('Match', fmt(d.ticket_match_quality)), item('Ambiguo', boolText(d.ticket_ambiguous)), item('Fuente', fmt(d.ticket_source))
      ].join(''), 'is-ticket'),
      section('HFC AUTO', [
        item('Estado operativo', fmt(d.estado_operativo_hfc_auto)), item('Descripción', fmt(d.descripcion), 'span-2'),
        item('Tipo match', fmt(d.tipo_match_hfc_auto)), item('Enriquecimiento', fmt(d.estado_enriquecimiento)), item('Fecha', fmt(d.fecha_hfc_auto))
      ].join('')),
      section('Espectro / Cobertura', [
        item('Disponibilidad', String(d.tecnologia || '').toUpperCase() === 'CASA' ? 'Consultar capturas reales disponibles' : 'N/D'),
        item('Nota', String(d.tecnologia || '').toUpperCase() === 'CASA'
          ? 'Cobertura parcial según capturas reales disponibles; no representa cobertura nacional completa.'
          : 'RF/espectro puede no estar disponible estructuralmente para este vendor.', 'span-2')
      ].join(''))
    ].join('');
  }

  async function fetchNode(node) {
    const root = ensureDrawer();
    openDrawer();
    q('#hfc-node-card-title', root).textContent = node || 'Nodo';
    q('#hfc-node-card-body', root).innerHTML = `<div class="hfc-node-card__loading">Consultando detalle real del nodo…</div>`;

    const url = new URL(endpoint, window.location.href);
    url.searchParams.set('resource', 'nodos');
    url.searchParams.set('limit', '20');
    url.searchParams.set('offset', '0');
    url.searchParams.set('search', node);

    const res = await fetch(url.toString(), { credentials: 'same-origin' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();
    const rows = payload.items || payload.data || payload.rows || [];
    const exact = rows.find(r => String(r.nodo || '').trim().toUpperCase() === String(node).trim().toUpperCase()) || rows[0];
    if (!exact) throw new Error('Nodo no encontrado en la respuesta');
    renderNode(exact);
  }

  function detectNodeFromRow(row) {
    if (!row) return '';
    if(row.dataset.node)return row.dataset.node;
    const table = row.closest('table');
    if (!table) return '';
    const headers = qa('thead th', table).map(th => String(th.textContent || '').trim().toUpperCase());
    const idx = headers.findIndex(h => h === 'NODO' || h.includes('NODO'));
    if (idx < 0) return '';
    const cells = qa('td', row);
    return (cells[idx]?.textContent || '').trim();
  }

  document.addEventListener('click', e => {
    const row = e.target.closest('table tbody tr');
    if (!row) return;
    if (e.target.closest('button,a,input,select,textarea,label')) return;
    const table = row.closest('table');
    if (!table) return;
    const headers = qa('thead th', table).map(th => String(th.textContent || '').trim().toUpperCase());
    if (!headers.some(h => h.includes('NODO'))) return;
    returnFocus=row;document.querySelectorAll('tr.is-selected').forEach(r=>r.classList.remove('is-selected'));row.classList.add('is-selected');
    const node = detectNodeFromRow(row);
    if (!node || node.length > 120) return;

    if(row.parentElement.id==='networkBody'){
      const d=window.__HFC_EXEC_CURRENT_ROWS__[Number(row.dataset.index)];
      if(!d)return;
      openDrawer();q('#hfc-node-card-title').textContent=d.service_group;
      q('#hfc-node-card-subtitle').textContent=[d.cmts,d.fabricante||d.vendor,d.ip].filter(Boolean).join(' · ');
      q('#hfc-node-card-body').innerHTML=section('Estado de la fuente local',item('Origen HFC',esc(q('#hfcAutoCmtsTime').textContent))+item('Estado',esc(d.observacion),'span-2'))+
        section('Módems',item('Total',esc(d.total_modems))+item('Offline',esc(d.offline))+item('% Offline',(Number(d.porc_offline||0)*100).toFixed(1)+'%'))+
        section('Incidente',item('Cruce',esc(d.inc_status),'span-2')+item('Identificador',esc(d.incidente||'—'),'span-2'))+
        section('Ubicación y catálogo',item('Ciudad',esc(d.zona))+item('IP CMTS',esc(d.ip||'—'))+item('Comunidad',esc(d.comunidad||'—'))+item('Aliado',esc(d.aliado||'—'))+item('Tipo',esc(d.tipo_elemento||'SERVICE GROUP'))+item('Descripción',esc(d.descripcion||'—'),'span-2'));
      return;
    }
    fetchNode(node).catch(err => {
      openDrawer();
      const body = q('#hfc-node-card-body');
      if (body) body.innerHTML = `<div class="hfc-node-card__error">No fue posible cargar el nodo: ${esc(err.message)}</div>`;
    });
  });

  document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('#networkBody tr')){e.preventDefault();e.target.click();}});
  ensureDrawer();
  console.info('[HFC Node Card] V51 corregido activo', CFG);
})();
window.addEventListener('rkp-hfc-data',e=>{
 const set=(id,text)=>{const el=document.getElementById(id);if(el)el.textContent=text;};
 set('header-monitoring','Dashboard HFC');set('header-connection','Conectado');
 set('header-sources',`${e.detail.total} elementos`);set('header-datetime',new Date().toLocaleString('es-CO'));
});

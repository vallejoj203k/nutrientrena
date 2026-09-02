#!/usr/bin/env python3
"""Genera el banco de pruebas del arrastre de días extrayendo el código REAL
de frontend/rutinas.html (no una copia), y lo deja en el mismo directorio.

Uso:  python3 tests/frontend/generar_harness.py && node tests/frontend/dias_arrastrar.test.js
"""
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src = open(os.path.join(RAIZ, 'frontend', 'rutinas.html')).read()
MODULO = open(os.path.join(RAIZ, 'frontend', 'js', 'routine-builder.js')).read()
MODULO_CSS = open(os.path.join(RAIZ, 'frontend', 'css', 'routine-builder.css')).read()

css = '\n'.join(re.findall(r'<style>(.*?)</style>', src, re.S)) + '\n' + MODULO_CSS

# El constructor vive en el módulo compartido, no en la página.
i = MODULO.index('function renderDaysList(){')
j = MODULO.index('\n  setupDayDrag();\n}\n', i) + len('\n  setupDayDrag();\n}\n')
render = MODULO[i:j]

a = MODULO.index('/* \u2500\u2500 Arrastrar d\u00edas')
b = MODULO.index('function startRenameDay(', a)
drag = MODULO[a:b]

harness = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head>
<body>
<div class="days-panel" style="width:260px"><div class="days-list" id="daysList"></div></div>
<script>
function esc(s){return String(s||'');}
let selectedDayIdx=0;
let routineData={days_list:[
  {day_name:'Lunes',blocks:[{exercises:[1,2,3]},{exercises:[4,5]}]},
  {day_name:'Martes',blocks:[{exercises:[1,2,3]},{exercises:[4,5]}]},
  {day_name:'Mi\u00e9rcoles',blocks:[{exercises:[1,2,3]}]},
]};
function renderBlocks(){}
function startRenameDay(){}
function duplicateDay(){}
function removeDay(){}
function selectDay(idx){selectedDayIdx=idx;renderDaysList();renderBlocks();}
%s
%s
window.__orden=()=>routineData.days_list.map(d=>d.day_name);
window.__sel=()=>selectedDayIdx;
renderDaysList();
</script></body></html>""" % (css, render, drag)

destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'harness.html')
open(destino, 'w').write(harness)
print('harness generado en', destino)

# ── Harness de las fechas del programa (client-profile.html) ────────────────
perfil = open(os.path.join(RAIZ, 'frontend', 'client-profile.html')).read()
a = perfil.index('/* Fechas en local, sin pasar por UTC')
b = perfil.index('async function saveDates()')
logica = perfil[a:b]

fechas = """<!doctype html><html><head><meta charset="utf-8"></head><body>
<input id="dt_start" type="date"><input id="dt_end" type="date"><input id="dt_weeks" type="number">
<div id="datesError"></div>
<script>
%s
</script></body></html>""" % logica

destino2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fechas.html')
open(destino2, 'w').write(fechas)
print('harness generado en', destino2)


# ── Harness del estado de carga al asignar planes (client-profile.html) ─────
css = '\n'.join(re.findall(r'<style>(.*?)</style>', perfil, re.S))
a = perfil.index('/* Animaci\u00f3n de la pantalla de carga')
b = perfil.index('async function renderEntrenamientoTab()')
carga = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head><body>
<div id="entrenamientoContent"></div><div id="nutricionContent"></div>
<script>
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;');}
%s
</script></body></html>""" % (css, perfil[a:b])

destino3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'carga.html')
open(destino3, 'w').write(carga)
print('harness generado en', destino3)


# ── Harness del constructor embebido en la ficha del cliente ───────────────
def _bloque(html, marca):
    i = html.index(marca); seg = html[i:]; prof = 0; j = 0
    while j < len(seg):
        if seg.startswith('<div', j): prof += 1
        elif seg.startswith('</div>', j):
            prof -= 1
            if prof == 0: j += 6; break
        j += 1
    return seg[:j]

cssp = ('\n'.join(re.findall(r'<style>(.*?)</style>', perfil, re.S))
        + '\n' + open(os.path.join(RAIZ, 'frontend', 'css', 'routine-builder.css')).read())
overlay = _bloque(perfil, '<div class="ne-backdrop" id="entBuilderOverlay">')
picker = _bloque(perfil, '<div class="picker-overlay" id="pickerOverlay"')
# El constructor ya no está inline: vive en el módulo compartido.
codigo = open(os.path.join(RAIZ, 'frontend', 'js', 'routine-builder.js')).read()

builder = """<!doctype html><html><head><meta charset="utf-8"><style>%s
.ne-backdrop{display:block !important;opacity:1 !important;visibility:visible !important;}
</style></head><body>
%s
%s
<script>
const API='http://x';
function h(){return{};}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function showToast(m){window.__toast=m;}
let pickerTargetBlockIdx=null, pickerReplaceEi=null;
let selectedDayIdx=0;
let routineData={name:'Rutina de fuerza',training:'Gimnasio',days_list:[
 {day_name:'Lunes',description:'',blocks:[
   {block_type:'normal',content:'',order_index:0,exercises:[
     {training_id:1,training_name:'Press de banca',muscle_group_name:'Pecho',series:3,repetitions:'12',break_time:60,intensity_type:'RPE',intensity_value:8,notes:'',order_index:0},
     {training_id:2,training_name:'Dominadas',muscle_group_name:'Espalda',series:3,repetitions:'8-12',break_time:60,intensity_type:'',intensity_value:null,notes:'',order_index:1}]},
   {block_type:'superset',content:'',order_index:1,exercises:[
     {training_id:3,training_name:'Extensiones triceps',muscle_group_name:'Triceps',series:2,repetitions:'10',break_time:60,intensity_type:'RPE',intensity_value:8,notes:'',order_index:0}]}]},
 {day_name:'Martes',description:'',blocks:[{block_type:'normal',content:'',order_index:0,exercises:[
     {training_id:4,training_name:'Sentadilla',muscle_group_name:'Pierna',series:4,repetitions:'8',break_time:90,intensity_type:'',intensity_value:null,notes:'',order_index:0}]}]},
 {day_name:'Mi\u00e9rcoles',description:'',blocks:[]}
]};
%s
window.__orden=()=>routineData.days_list.map(d=>d.day_name);
window.__ejercicios=()=>routineData.days_list[selectedDayIdx].blocks.map(b=>b.exercises.map(e=>e.training_name));
renderDaysList(); renderBlocks();
</script></body></html>""" % (cssp, overlay, picker, codigo)

destino4 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'builder.html')
open(destino4, 'w').write(builder)
print('harness generado en', destino4)


def _modulo(nombre):
    """Un fichero de `frontend/js/`, para incrustarlo en el harness.

    Los harness no tienen servidor: no pueden cargar `<script src>`. Y las
    páginas ya no llevan la cuenta de macros dentro — está en un módulo
    compartido con el servidor. Sin incrustarlo aquí, el harness revienta con
    "macrosAlimento is undefined" mientras la página real funciona.
    """
    return open(os.path.join(RAIZ, 'frontend', 'js', nombre)).read()


# ── Harness del previo de dietas al asignar ────────────────────────────────
i = perfil.index('/* Cantidad de una fila y su unidad')
j = perfil.index('function toggleDietPreview(', i)

prev = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head>
<body><div class="dietpick-detail" id="out"></div>
<script>%s</script>
<script>
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
%s
window.__pinta=(m)=>{document.getElementById('out').innerHTML=_dietpickComida(m);};
</script></body></html>""" % (cssp, _modulo('macros-alimento.js'), perfil[i:j])

destino5 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview.html')
open(destino5, 'w').write(prev)
print('harness generado en', destino5)


# ── Harness de la biblioteca agrupada por organización (diets.html) ────────
dts = open(os.path.join(RAIZ, 'frontend', 'diets.html')).read()
cssd = '\n'.join(re.findall(r'<style>(.*?)</style>', dts, re.S))
a = dts.index('/* \u2500\u2500 Biblioteca agrupada por organizaci\u00f3n')
b = dts.index('function renderTable(diets) {')
logica = dts[a:b]
c = dts.index('function renderTable(diets) {')
d = dts.index('\n}\n', dts.index("return;\n  }\n  tb.innerHTML = grupos.map", c)) + 3
render = dts[c:d]

grupos = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head><body>
<div class="lib-table-wrap"><table class="lib-table"><tbody id="dietsTbody"></tbody></table></div>
<span id="dietTotalLabel"></span><span id="subcountDietas"></span>
<script>
var API='http://x', token='t', allDiets=[];
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function dietRow(d){return '<tr class="fila" data-org="'+(d.organization_id==null?'plat':d.organization_id)+'"><td colspan="8">'+esc(d.title)+'</td></tr>';}
function applyFilter(){ renderTable(window.__datos); }
%s
%s
window.__pinta=(datos,nombres)=>{window.__datos=datos;_orgNombres=nombres;_grpCerrados={};renderTable(datos);};
</script></body></html>""" % (cssd, logica, render)

destino6 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grupos.html')
open(destino6, 'w').write(grupos)
print('harness generado en', destino6)


# ── Harness de la ejecución de un ejercicio ────────────────────────────────
# Se saca el pintado de la pantalla real, no una copia: si diverge, la copia
# pasaría las pruebas mientras la página se rompe.
ejs = open(os.path.join(RAIZ, 'frontend', 'ejercicios.html')).read()
csse = '\n'.join(re.findall(r'<style>(.*?)</style>', ejs, re.S))
a = ejs.index('  // Hacer caso a lo que el autor escribió')
b = ejs.index("    :'';", ejs.index('const execHtml=', a)) + len("    :'';")
pintado = ejs[a:b]

pasos = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head><body>
<div id="out"></div>
<script>%s</script>
<script>
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
window.__pinta=(texto)=>{
  const ex={description:texto};
%s
  document.getElementById('out').innerHTML=execHtml;
};
</script></body></html>""" % (csse, _modulo('pasos-ejecucion.js'), pintado)

destino7 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pasos.html')
open(destino7, 'w').write(pasos)
print('harness generado en', destino7)


# ── Harness de la lista de la compra ───────────────────────────────────────
# Solo el módulo: las cuentas son lo que puede salir mal, y no necesitan
# pantalla para comprobarse.
lista = """<!doctype html><html><head><meta charset="utf-8"></head><body>
<script>%s</script>
</body></html>""" % _modulo('lista-compra.js')

destino8 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lista.html')
open(destino8, 'w').write(lista)
print('harness generado en', destino8)


# ── Harness del Resumen de Progreso ────────────────────────────────────────
# El alto de la gráfica es lo que se comprueba, y el alto solo existe cuando
# hay una pantalla midiendo: en el código fuente no se ve. Por eso se saca la
# página real con su CSS y se mide con el navegador.
a = perfil.index('function _renderPgResumen() {')
b = perfil.index('/* ══', perfil.index('function _buildLatestCiSection()'))
resumen_js = perfil[a:b]

resumen = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head>
<body style="margin:0">
<div id="marco" style="width:1400px">
  <div class="pg-subtabs-bar">
    <button class="pg-stab active" onclick="showProgresoSubtab('resumen',this)">Resumen</button>
    <button class="pg-stab" onclick="showProgresoSubtab('fuerza',this)">Fuerza</button>
    <button class="pg-stab" onclick="showProgresoSubtab('checkins',this)">Check-ins</button>
  </div>
  <div id="pg-pane-resumen" class="pg-subpane"></div>
  <div id="pg-pane-fuerza" class="pg-subpane" style="display:none">fuerza</div>
  <div id="pg-pane-checkins" class="pg-subpane" style="display:none">checkins</div>
</div>
<script>
const API='http://x'; const clientId=1;
function h(){return{};}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function openTargetModal(){window.__metas=true;}
function showProgresoSubtab(name,btn){
  document.querySelectorAll('.pg-stab').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.pg-subpane').forEach(p=>p.style.display='none');
  if(btn) btn.classList.add('active');
  const pane=document.getElementById('pg-pane-'+name); if(pane) pane.style.display='';
}
var checkins=[], clientData={}, _target=null, clientRoutines=[];
var _fzDatos=null, _fzCargando=false;
%s
window.__pinta=(ck,cd,tg,fz)=>{
  checkins=ck; clientData=cd||{}; _target=tg; _fzDatos=(fz===undefined?[]:fz);
  _resFzError=false; _renderPgResumen();
};
</script></body></html>""" % (cssp, resumen_js)

destino9 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resumen.html')
open(destino9, 'w').write(resumen)
print('harness generado en', destino9)


# ── Harness de la unidad del alimento y del previo de la dieta ─────────────
# El previo se saca de diets.html tal cual, no copiado: el fallo era
# justamente que esa pantalla deducía la unidad por su cuenta y de forma
# distinta al editor que hay dos clics más allá.
dts2 = open(os.path.join(RAIZ, 'frontend', 'diets.html')).read()
# `dppMeals` se pinta en tres sitios de la pagina; el que interesa es el que
# lleva la unidad, asi que se ancla ahi y se retrocede hasta su principio.
ancla = dts2.index("var itemKcal = Math.round(window.macrosAlimento.escalar(al.calories, al, qty));")
i = dts2.rindex("document.getElementById('dppMeals').innerHTML =", 0, ancla)
j = dts2.index("    var title = esc(d.title || '');", ancla)
pinta_previo = dts2[i:j]

unidades = """<!doctype html><html><head><meta charset="utf-8"></head><body>
<div id="dppMeals"></div>
<script>%s</script>
<script>
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
window.__previo=(d)=>{
%s
};
</script></body></html>""" % (_modulo('macros-alimento.js'), pinta_previo)

destino10 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'unidades.html')
open(destino10, 'w').write(unidades)
print('harness generado en', destino10)


# ── Harness de las fotos de progreso del cliente ───────────────────────────
# Se saca el pintado y el borrado de client-progreso.html tal cual: lo que hay
# que comprobar es que el boton aparece, que pregunta antes y que pide el
# borrado del angulo correcto.
prg = open(os.path.join(RAIZ, 'frontend', 'client-progreso.html')).read()
cssg = '\n'.join(re.findall(r'<style>(.*?)</style>', prg, re.S))
a = prg.index('  function setTab(t){')
b = prg.index('  function render(){')
pinta = prg[a:b]
# Se ancla en la variable, no en el comentario: el mismo texto encabeza el
# bloque de CSS, y buscando el comentario se extraia media pagina.
c = prg.rindex('/*', 0, prg.index('  var _porBorrar = null;'))
d = prg.index("  function pickPhoto(){")
borra = prg[c:d]
dialogo = _bloque(prg, '<div class="ask-back" id="askBack">')

fotos = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head><body>
<button class="ptab sel" id="tab-frontal"></button>
<button class="ptab" id="tab-lateral"></button>
<button class="ptab" id="tab-espalda"></button>
<div id="photos"></div>
%s
<div class="toast" id="toast"></div>
<script>
const API='http://x';
function headers(){return{'Content-Type':'application/json'};}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/'/g,'&#39;');}
function fmtDate(d){return String(d||'');}
function toast(m,e){window.__toast=m;window.__err=!!e;}
var _tab='frontal', _data={};
window.__llamadas=[];
window.fetch=function(url,opt){
  window.__llamadas.push({url:url,metodo:(opt&&opt.metodo)||(opt&&opt.method)||'GET'});
  return Promise.resolve({ok:!window.__falla, json:()=>Promise.resolve({})});
};
async function loadProgress(){ window.__recargado=(window.__recargado||0)+1; }
%s
%s
window.__pinta=(datos,tab)=>{_data=datos;_tab=tab||'frontal';renderPhotos();};
document.getElementById('askSi').onclick = borrarFoto;
</script></body></html>""" % (cssg, dialogo, pinta, borra)

destino11 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fotos.html')
open(destino11, 'w').write(fotos)
print('harness generado en', destino11)


# ── Harness de la hoja del RPE ─────────────────────────────────────────────
# Se extrae de client-entrena.html el pintado de la sesion y la hoja, tal
# cual: lo que hay que comprobar es que el numero que se guarda sigue siendo
# el RPE de siempre aunque al cliente se le pregunte por repeticiones.
ent = open(os.path.join(RAIZ, 'frontend', 'client-entrena.html')).read()
csse2 = '\n'.join(re.findall(r'<style>(.*?)</style>', ent, re.S))
a = ent.index('  function prevText(e, si){')
b = ent.index('  function wsToggle(ei, si){')
codigo_ws = ent[a:b]
hoja_html = _bloque(ent, '<div class="rpe-back" id="rpeBack"')

rpe = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head><body>
<div id="wsInner"></div>
%s
<script>
function esc(s){ if(s==null)return''; return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
var _ws=null;
function _wsThumb(e){ return '<div class="ws-thumb"></div>'; }
%s
window.__pinta=(ex)=>{_ws={exercises:ex};renderWorkout();};
window.__series=()=>_ws.exercises.map(e=>e.sets.map(s=>s.rpe));
</script></body></html>""" % (csse2, hoja_html, codigo_ws)

destino12 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rpe.html')
open(destino12, 'w').write(rpe)
print('harness generado en', destino12)


# ── Harness del menú de "…" de la fila ─────────────────────────────────────
# Se monta la tabla REAL con su CSS real, porque el fallo no estaba en el
# menú sino en el `overflow` de la tabla que lo contenía: con una tabla de
# mentira no se reproduciria.
dts3 = open(os.path.join(RAIZ, 'frontend', 'diets.html')).read()
cssm = '\n'.join(re.findall(r'<style>(.*?)</style>', dts3, re.S))

filas = ''.join(["""<tr class="fila"><td class="lib-td-name">Dieta %d</td>
  <td class="lib-actions">
    <button class="lib-btn-assign">Asignar</button>
    <div class="lib-menu-wrap">
      <button class="lib-icon-btn mas-btn" onclick="menuFila.abrir(event,this)">...</button>
      <div class="lib-menu-dd">
        <div class="lib-menu-item">Editar</div>
        <div class="lib-menu-item">Duplicar</div>
        <div class="lib-menu-item danger">Eliminar</div>
      </div>
    </div>
  </td></tr>""" % i for i in range(1, 31)])

menu = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head>
<body style="margin:0">
<div class="main" style="height:100vh">
  <div class="lib-table-wrap" id="wrap">
    <table class="lib-table"><tbody id="cuerpo">%s</tbody></table>
  </div>
</div>
<script>%s</script>
<script>
/* Como lo hace ejercicios.html: se fabrica el menu y se cuelga del body. */
window.__suelto=(btn)=>{
  var m=document.createElement('div');
  m.className='row-menu';
  m.style.cssText='position:fixed;background:#fff;border:1px solid #E5E7EB;border-radius:10px;'+
    'box-shadow:0 8px 24px rgba(0,0,0,.12);z-index:300;min-width:170px;overflow:hidden;';
  // Con los estilos EN LÍNEA que pone ejercicios.html: sin ellos los botones
  // salen de 7 px, el menú entero cabe en cualquier hueco y la prueba no
  // distingue nada.
  var est='display:flex;align-items:center;gap:8px;width:100%%;padding:10px 14px;'+
    'font-size:13px;color:#374151;background:none;border:none;cursor:pointer;text-align:left;';
  m.innerHTML=['Editar','Ver video','Duplicar','Archivar','Eliminar'].map(function(t){
    return '<button class="lib-menu-item" style="'+est+'">'+t+'</button>';
  }).join('');
  document.body.appendChild(m);
  menuFila.suelto(m, btn);
};
window.__soloUna=()=>{
  var c=document.getElementById('cuerpo');
  Array.prototype.slice.call(c.rows,1).forEach(function(r){c.removeChild(r);});
};
</script></body></html>""" % (cssm, filas, _modulo('menu-fila.js'))

destino13 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'menu.html')
open(destino13, 'w').write(menu)
print('harness generado en', destino13)


# ── Harness del selector de modo de programación ───────────────────────────
# Se saca de client-profile.html el selector y el cambio de modo tal cual. Lo
# que hay que comprobar es que las dos areas (nutricion y entrenamiento) son
# independientes, y eso solo se ve ejecutando el codigo de verdad.
a = perfil.index('var _nutModo = null;')
b = perfil.index('/* La calculadora, con el resumen en la cabecera')
tarjetas = perfil[a:b]
c = perfil.index('/* \u2500\u2500 Cambiar de modo \u2500')
d = perfil.index('/* Re-renderiza solo el planificador')
cambio = perfil[c:d]
modal = _bloque(perfil, '<div class="cmodo-back" id="cmodoBack"')

modos = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head><body>
<div id="nutricionContent"></div>
<div id="entrenamientoContent"></div>
%s
<script>
const API='http://x'; const clientId='cli-1';
function h(){return{};}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function showToast(m,t){window.__toast=m;window.__toastTipo=t;}
function showTab(n){window.__pestana=n;}
function renderCalendarioTab(){window.__calendario=(window.__calendario||0)+1;}
async function renderNutricionTab(){document.getElementById('nutricionContent').innerHTML=_nutModoCardHTML();}
async function renderEntrenamientoTab(){document.getElementById('entrenamientoContent').innerHTML=_entModoCardHTML();}
var clientData={};
window.__puestas=[];
window.fetch=function(url,opt){
  window.__puestas.push({url:url, metodo:opt&&opt.method, cuerpo:opt&&opt.cuerpo||opt&&opt.body});
  return Promise.resolve({ok:!window.__falla, json:()=>Promise.resolve({})});
};
%s
%s
window.__pinta=(nut,ent)=>{
  _nutModo=nut; _entModo=ent; _calSalirEnfoque=false; window.__puestas=[];
  document.getElementById('nutricionContent').innerHTML=_nutModoCardHTML();
  document.getElementById('entrenamientoContent').innerHTML=_entModoCardHTML();
};
window.__modos=()=>({nut:_nutModo, ent:_entModo});
</script></body></html>""" % (cssp, modal, tarjetas, cambio)

destino14 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modos.html')
open(destino14, 'w').write(modos)
print('harness generado en', destino14)


# ── Harness del carril de la distribución semanal ──────────────────────────
# Se saca de client-profile.html el carril y la etiqueta del modal, tal cual:
# el punto de todo esto es que las dos llamen igual a la misma dieta, y con
# una copia eso no se comprueba.
a = perfil.index('/* El carril de la izquierda: la distribución semanal')
b = perfil.index('function _renderNutUI() {')
carril = perfil[a:b]
c = perfil.index('function _wdEtiqueta(d, i) {')
d = perfil.index('\n}\n', c) + 3
etiqueta = perfil[c:d]

dist = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head><body>
<div class="nut-day-side" id="carril" style="width:175px"></div>
<script>
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
const _NUT_DAY_ABV  = ['LUN','MAR','MI\u00c9','JUE','VIE','S\u00c1B','DOM'];
var clientDiets=[], _nutFoco='dia', _nutDayIdx=0, _nutActiveDietIdx=0;
window.__clicks=[];
function selectNutDay(i){window.__clicks.push('dia:'+i);}
function selectNutDiet(i){window.__clicks.push('dieta:'+i);}
function openWeekDistModal(){window.__clicks.push('distribucion');}
function openAssignDietModal(){window.__clicks.push('anadir');}
%s
%s
window.__pinta=(dietas, dias, foco, idx)=>{
  clientDiets=dietas; _nutFoco=foco||'dia';
  if(foco==='dieta') _nutActiveDietIdx=idx||0; else _nutDayIdx=idx||0;
  window.__clicks=[];
  document.getElementById('carril').innerHTML=_nutCarrilHTML(dias);
};
</script></body></html>""" % (cssp, etiqueta, carril)

destino15 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'distribucion.html')
open(destino15, 'w').write(dist)
print('harness generado en', destino15)


# ── Harness del panel del plan (cabecera + comidas) ────────────────────────
# Se saca de client-profile.html el pintado del plan tal cual, para poder
# comprobar las cifras, las unidades de cada fila y a dónde llevan los botones.
# Ojo: "Planificador de macros" aparece tambien en el CSS, mucho antes. Se
# busca DESPUES de la funcion, o el corte sale vacio.
a = perfil.index('function _nutTotalesDe(detail) {')
b = perfil.index('let _nutPlanner = null;', a)
totales = perfil[a:b]
a2 = perfil.index('/* La cabecera del plan: el degradado')
b2 = perfil.index('function _renderNutUI() {')
hero = perfil[a2:b2]
c = perfil.index("        }).join('')}</div>")
c0 = perfil.rindex('foods.map(meal=>{', 0, c)
comidas = perfil[c0:c]

plan = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head>
<body style="margin:0;background:#F8FAFC"><div id="plan" style="padding:18px;max-width:900px"></div>
<script>%s</script>
<script>
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function _nutMealKcal(meal){return (meal.detail||[]).reduce((s,i)=>{const a=i.aliment||{};
  return s+window.macrosAlimento.escalar(a.calories,a,i.quantity_calc||0);},0);}
function _nutTotalKcal(d){return (d.foods||[]).reduce((s,m)=>s+_nutMealKcal(m),0);}
var _HORAS={'Desayuno':'08:00','Media mañana':'11:00','Comida':'14:00'};
function _nutMealTime(n){return _HORAS[n]||'';}
window.__acciones=[];
function openNutEditor(){window.__acciones.push('editar');}
const API='http://x';
var _nutMenuVeces=null, _nutFoco='dia', _nutDayIdx=0, _nutActiveDietIdx=0;
var clientDiets=[], _nutDetail=null, _nutMenu=null;
function _nutMenuDays(){return _nutMenuVeces;}
function showToast(m,t){window.__acciones.push('toast:'+m);}
function _downloadPlanPdf(url,fichero){window.__acciones.push('pdf:'+url+'|'+fichero);}
%s
function removeNutPlan(){window.__acciones.push('borrar');}
%s
%s
window.__estado=(menu,foco,dia,dietas,det)=>{
  _nutMenuVeces=menu; _nutFoco=foco||'dia'; _nutDayIdx=dia||0;
  clientDiets=dietas||[]; _nutDetail=det||null; window.__acciones=[];
};
window.__pinta=(det,mirandoDia,dayName)=>{
  window.__acciones=[];
  const totalKcal=Math.round(_nutTotalKcal(det))||Math.round(det.calories||0);
  const foods=det.foods||[];
  document.getElementById('plan').innerHTML=
    _nutHeroHTML(det,{mirandoDia:!!mirandoDia,dayName:dayName||'Lunes',dayHasDiet:true,totalKcal})
    + '<div class="nut-meals-area">' + %s}).join('') + '</div>';
};
</script></body></html>"""

d0 = perfil.index('function _downloadNutPdf(ev) {')
d1 = perfil.index('\n}\n', d0) + 3
descarga = perfil[d0:d1]

destino16 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plan.html')
open(destino16, 'w').write(
    plan % (cssp, _modulo('macros-alimento.js'), descarga, totales, hero, comidas))
print('harness generado en', destino16)


# ── Harness del plan de entrenamiento ──────────────────────────────────────
# El carril y la tabla del día, sacados de client-profile.html. Lo que hay que
# comprobar es el REPARTO: qué día de la semana toca cada día de la rutina.
a = perfil.index('/* Los días de la semana, para el carril y para el PDF. */')
b = perfil.index('function selectEntDay(')
ent = perfil[a:b]

entre = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head>
<body style="margin:0;background:#F8FAFC">
<div id="entrenamientoContent" style="padding:16px;max-width:1100px"></div>
<script>
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
var clientRoutines=[], clientData={}, _entSelectedDay=0, _entModo='semanal';
window.__acciones=[];
function _entModoCardHTML(){return '';}
function loadSessions(){}
function openSessionModal(){}
function openEntBuilder(i){window.__acciones.push('editor:'+i);}
function _downloadEntPdf(){window.__acciones.push('pdf');}
function changeEntPlan(){window.__acciones.push('cambiar');}
function removeEntPlan(){window.__acciones.push('borrar');}
function selectEntDay(i){_entSelectedDay=i;_renderEntTrainingUI();}
%s
window.__pinta=(rutina,sel)=>{
  clientRoutines=[rutina]; _entSelectedDay=sel||0; window.__acciones=[];
  _renderEntTrainingUI();
};
</script></body></html>""" % (cssp, ent)

destino17 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'entreno.html')
open(destino17, 'w').write(entre)
print('harness generado en', destino17)

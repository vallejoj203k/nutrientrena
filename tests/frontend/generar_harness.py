#!/usr/bin/env python3
"""Genera el banco de pruebas del arrastre de días extrayendo el código REAL
de frontend/rutinas.html (no una copia), y lo deja en el mismo directorio.

Uso:  python3 tests/frontend/generar_harness.py && node tests/frontend/dias_arrastrar.test.js
"""
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src = open(os.path.join(RAIZ, 'frontend', 'rutinas.html')).read()

css = '\n'.join(re.findall(r'<style>(.*?)</style>', src, re.S))

i = src.index('function renderDaysList(){')
j = src.index('\n  setupDayDrag();\n}\n', i) + len('\n  setupDayDrag();\n}\n')
render = src[i:j]

a = src.index('/* \u2500\u2500 Arrastrar d\u00edas')
b = src.index('function startRenameDay(', a)
drag = src[a:b]

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
a = perfil.index('function _tabSetLoading(')
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

cssp = '\n'.join(re.findall(r'<style>(.*?)</style>', perfil, re.S))
overlay = _bloque(perfil, '<div class="ne-backdrop" id="entBuilderOverlay">')
picker = _bloque(perfil, '<div class="picker-overlay" id="pickerOverlay"')
i = perfil.index('function addDay(){')
j = perfil.index('/* \u2500\u2500 Save \u2500\u2500 */', i)
codigo = perfil[i:j]

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


# ── Harness del previo de dietas al asignar ────────────────────────────────
i = perfil.index('function _dietpickComida(m) {')
j = perfil.index('function toggleDietPreview(', i)

prev = """<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head>
<body><div class="dietpick-detail" id="out"></div>
<script>
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
%s
window.__pinta=(m)=>{document.getElementById('out').innerHTML=_dietpickComida(m);};
</script></body></html>""" % (cssp, perfil[i:j])

destino5 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview.html')
open(destino5, 'w').write(prev)
print('harness generado en', destino5)

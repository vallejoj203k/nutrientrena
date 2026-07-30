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

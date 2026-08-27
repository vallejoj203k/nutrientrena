const { chromium } = require('../_pw');
(async()=>{
  const b=await chromium.launch(); const p=await b.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push(String(e)));
  await p.goto('file://'+__dirname+'/builder.html');
  let f=0; const ck=(n,c,x)=>{console.log((c?'OK   ':'FALLO ')+n+(c?'':' -> '+JSON.stringify(x)));if(!c)f++;};

  ck('sin errores de JS al renderizar', errs.length===0, errs);
  ck('3 dias pintados', await p.locator('#daysList .day-chip').count()===3);
  // Lo que faltaba en la copia vieja:
  ck('los dias tienen contador de bloques/ejercicios', await p.locator('#daysList .day-chip-sub').count()===3);
  const sub = await p.locator('#daysList .day-chip').first().locator('.day-chip-sub').textContent();
  ck('el contador dice lo correcto', /2 bloques.*3 ejercicios/.test(sub), sub);
  ck('los dias tienen asa de arrastre', await p.locator('#daysList .day-grip').count()===3);
  ck('existe setupDayDrag', await p.evaluate(()=>typeof setupDayDrag)==='function');
  ck('existe moveExercise', await p.evaluate(()=>typeof moveExercise)==='function');
  ck('existe el buscador nuevo', await p.evaluate(()=>typeof loadPickerCatalog)==='function' && await p.evaluate(()=>typeof renderPkGrid)==='function');

  // Bloques y tabla de ejercicios en su formato nuevo
  ck('2 bloques en el dia 1', await p.locator('#blocksList .blk').count()===2);
  ck('la tabla usa el formato nuevo (.ex-row2)', await p.locator('#blocksList .ex-row2').count()===3, await p.locator('#blocksList .ex-row2').count());
  ck('hay botones de mover arriba/abajo', await p.locator('#blocksList .ex-move').count()>0);

  // Mover un ejercicio
  await p.evaluate(()=>moveExercise(0,0,1));
  ck('moveExercise reordena', JSON.stringify(await p.evaluate(()=>__ejercicios()[0]))==='["Dominadas","Press de banca"]', await p.evaluate(()=>__ejercicios()[0]));

  // Cambiar de dia
  await p.evaluate(()=>selectDay(1));
  ck('cambiar de dia repinta', await p.locator('#blocksList .ex-row2').count()===1);
  ck('el titulo del dia se actualiza', (await p.textContent('#selectedDayName')).includes('Martes'), await p.textContent('#selectedDayName'));

  // Arrastrar dias funciona tambien aqui
  const g=p.locator('#daysList .day-chip').nth(0).locator('.day-grip');
  const t=p.locator('#daysList .day-chip').nth(2);
  const gb=await g.boundingBox(), tb=await t.boundingBox();
  await p.mouse.move(gb.x+gb.width/2, gb.y+gb.height/2); await p.mouse.down();
  await p.mouse.move(gb.x+gb.width/2, gb.y+20,{steps:5});
  await p.mouse.move(tb.x+tb.width/2, tb.y+tb.height-4,{steps:12}); await p.mouse.up();
  await p.waitForTimeout(120);
  ck('los dias se arrastran en el modal', JSON.stringify(await p.evaluate(()=>__orden()))==='["Martes","Miércoles","Lunes"]', await p.evaluate(()=>__orden()));

  // Notas del dia y fila de anadir bloque
  ck('existe la fila de anadir bloque', await p.locator('#blockAddRow .block-add-btn').count()===4);
  ck('existen las notas del dia', await p.locator('#dayNotes').count()===1);

  // ── El buscador del selector, que filtra en el navegador ──────────────────
  // No pasa por el servidor, asi que la busqueda por sinonimos hay que
  // resolverla aqui aparte. Si no, "bench press" encuentra el ejercicio en la
  // pagina de Ejercicios y no al montar una rutina, que es donde mas se busca.
  await p.evaluate(()=>{
    _pkTrainings=[
      {id:1,name:'Press de banca',muscle_group_name:'Pecho',aliases:'Bench press, Press banca plano'},
      {id:2,name:'Sentadilla',muscle_group_name:'Pierna',aliases:null},
    ];
    buildPkGroups(); pickerMgFilter='Pecho';
  });
  const buscar=async q=>{
    await p.evaluate(v=>{document.getElementById('pickerSearch').value=v;},q);
    await p.evaluate(()=>renderPkGrid());
    return await p.evaluate(()=>_pkView.map(t=>t.name));
  };
  ck('el selector encuentra por sinonimo',
     JSON.stringify(await buscar('bench press'))==='["Press de banca"]', await buscar('bench press'));
  ck('el selector sigue encontrando por el nombre',
     JSON.stringify(await buscar('Sentadilla'))==='["Sentadilla"]', await buscar('Sentadilla'));
  // Con `aliases` a null, concatenar sin cuidado deja un "null" que casa con
  // cualquiera que escriba esa palabra.
  ck('un ejercicio sin sinonimos no aparece por "null"',
     JSON.stringify(await buscar('null'))==='[]', await buscar('null'));

  ck('sin errores de JS al final', errs.length===0, errs);
  await b.close(); process.exit(f?1:0);
})();

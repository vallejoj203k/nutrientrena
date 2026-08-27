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

  // ── Las series recomendadas del ejercicio llegan a la rutina ──────────────
  // Estaban guardadas en la ficha y se tiraban al anadirlo: el coach las volvia
  // a escribir a mano una por una, teniendolas delante en la ficha.
  await p.evaluate(()=>{
    _pkTrainings=[
      {id:9,name:'Remo con banda',muscle_group_name:'Espalda',rec_series:'3',rec_reps:'10',rec_rest:'60'},
      {id:10,name:'Plancha',muscle_group_name:'Core',rec_series:'3-4',rec_reps:'8-12',rec_rest:'60-90s'},
      {id:11,name:'Sin recomendar',muscle_group_name:'Core'},
    ];
    buildPkGroups(); pickerMgFilter='Espalda';
  });
  const anadir=async (idx)=>{
    await p.evaluate(()=>{document.getElementById('pickerSearch').value='';});
    await p.evaluate(i=>{openPicker(0);_pkView=_pkTrainings;pkPick(i);}, idx);
    const day=await p.evaluate(()=>routineData.days_list[selectedDayIdx].blocks[0].exercises);
    return day[day.length-1];
  };

  await p.evaluate(()=>selectDay(0));
  let nuevo=await anadir(0);
  ck('las series recomendadas llegan a la rutina',
     nuevo.series===3 && nuevo.repetitions==='10' && nuevo.break_time===60,
     {series:nuevo.series,reps:nuevo.repetitions,desc:nuevo.break_time});

  nuevo=await anadir(1);
  // "3-4" y "60-90s" son texto libre; las casillas de la rutina son numericas.
  ck('un rango se convierte en el primer numero',
     nuevo.series===3 && nuevo.break_time===60, {series:nuevo.series,desc:nuevo.break_time});
  ck('las repeticiones se copian tal cual, que ya son un rango',
     nuevo.repetitions==='8-12', nuevo.repetitions);

  nuevo=await anadir(2);
  ck('un ejercicio sin recomendaciones entra en blanco, no con "NaN"',
     nuevo.series===null && nuevo.repetitions==='' && nuevo.break_time===null,
     {series:nuevo.series,reps:nuevo.repetitions,desc:nuevo.break_time});

  // Y al CAMBIAR un ejercicio no se pisa lo que el coach ya habia escrito.
  await p.evaluate(()=>{
    const ex=routineData.days_list[selectedDayIdx].blocks[0].exercises;
    ex[ex.length-1].series=5; ex[ex.length-1].repetitions='20';
    openPicker(0, ex.length-1); _pkView=_pkTrainings; pkPick(0);
  });
  const cambiado=await p.evaluate(()=>{
    const ex=routineData.days_list[selectedDayIdx].blocks[0].exercises;
    return ex[ex.length-1];
  });
  ck('al cambiar de ejercicio no se pisan las series que escribio el coach',
     cambiado.series===5 && cambiado.repetitions==='20', {series:cambiado.series,reps:cambiado.repetitions});
  ck('pero si rellena lo que estaba vacio', cambiado.break_time===60, cambiado.break_time);

  ck('sin errores de JS al final', errs.length===0, errs);
  await b.close(); process.exit(f?1:0);
})();

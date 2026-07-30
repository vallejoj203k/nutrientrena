const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async()=>{
  const b=await chromium.launch(); const p=await b.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push(String(e)));
  await p.goto('file://'+__dirname+'/preview.html');
  let f=0; const ck=(n,c,x)=>{console.log((c?'OK   ':'FALLO ')+n+(c?'':' -> '+JSON.stringify(x)));if(!c)f++;};

  // Comida real como la devuelve /diets/findAll
  await p.evaluate(()=>__pinta({name:'Desayuno',time:'07:00',detail:[
    {id:1,quantity:100,aliment:{name:'Huevo entero, cocido, frito',calories:196,quantity_unit:'g'}},
    {id:2,quantity:10,aliment:{name:'Aceite de almendra',calories:884,quantity_unit:'g'}},
    {id:3,quantity:50,aliment:{name:'Lentejas germinadas',calories:101,quantity_unit:'g'}},
  ]}));
  const t = await p.textContent('#out');
  ck('sale la cabecera de la comida', t.includes('Desayuno') && t.includes('· 07:00'), t);
  ck('AHORA se ven los alimentos', await p.locator('.dietpick-food').count()===3, await p.locator('.dietpick-food').count());
  ck('sale el nombre del alimento', t.includes('Huevo entero, cocido, frito'));
  ck('la cantidad va a la derecha con unidad', t.includes('100 gr') && t.includes('10 gr') && t.includes('50 gr'), t);
  // 196 + 88.4 + 50.5 = 334.9 -> 335
  ck('kcal TOTAL de la comida', (await p.textContent('.dietpick-meal-kcal')) === '335 kcal', await p.textContent('.dietpick-meal-kcal'));
  ck('ya no hay kcal por alimento', await p.locator('.dietpick-food-kcal').count()===0);

  // Sin alimentos
  await p.evaluate(()=>__pinta({name:'Cena',time:'21:00',detail:[]}));
  const t2=await p.textContent('#out');
  ck('comida vacia se explica', t2.includes('Sin alimentos en esta comida'), t2);
  ck('comida vacia no muestra 0 kcal', await p.locator('.dietpick-meal-kcal').count()===0);

  // Datos incompletos no revientan
  await p.evaluate(()=>__pinta({name:'Comida',detail:[{id:9},{id:10,quantity:80,aliment:{name:'Sin kcal'}}]}));
  const t3=await p.textContent('#out');
  ck('aguanta detail sin aliment', t3.includes('Alimento'), t3);
  ck('sin kcal no inventa un 0', !/\b0 kcal\b/.test(t3), t3);
  ck('la fila sin cantidad no pinta unidad suelta', !/\bundefined\b/.test(t3), t3);

  // Escapado
  await p.evaluate(()=>__pinta({name:'<img src=x>',detail:[{id:1,quantity:1,aliment:{name:'<b>ojo</b>',calories:100}}]}));
  ck('escapa el HTML', (await p.innerHTML('#out')).includes('&lt;b&gt;ojo'), await p.innerHTML('#out'));

  // Unidades que no son gramos se respetan
  await p.evaluate(()=>__pinta({name:'Merienda',detail:[
    {id:1,quantity:250,aliment:{name:'Leche',calories:42,quantity_unit:'ml'}},
    {id:2,quantity:2,aliment:{name:'Tostada',calories:80,quantity_type:{description:'ud'}}}]}));
  const t4=await p.textContent('#out');
  ck('respeta ml y ud', t4.includes('250 ml') && t4.includes('2 ud'), t4);

  ck('sin errores de JS', errs.length===0, errs);
  await b.close(); process.exit(f?1:0);
})();

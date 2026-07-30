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
  ck('sale la cabecera de la comida', t.includes('Desayuno · 07:00') && t.includes('3 alimentos'), t);
  ck('AHORA se ven los alimentos', await p.locator('.dietpick-food').count()===3, await p.locator('.dietpick-food').count());
  ck('sale el nombre del alimento', t.includes('Huevo entero, cocido, frito'));
  ck('sale la cantidad', t.includes('· 100g'), t);
  ck('kcal reescaladas a la cantidad', t.includes('196 kcal') && t.includes('88 kcal') && t.includes('51 kcal'), t);

  // Sin alimentos
  await p.evaluate(()=>__pinta({name:'Cena',time:'21:00',detail:[]}));
  const t2=await p.textContent('#out');
  ck('comida vacia se explica', t2.includes('0 alimentos') && t2.includes('Sin alimentos en esta comida'), t2);

  // Datos incompletos no revientan
  await p.evaluate(()=>__pinta({name:'Comida',detail:[{id:9},{id:10,quantity:80,aliment:{name:'Sin kcal'}}]}));
  const t3=await p.textContent('#out');
  ck('aguanta detail sin aliment', t3.includes('Alimento'), t3);
  ck('sin kcal no inventa un 0', !/\b0 kcal\b/.test(t3), t3);

  // Escapado
  await p.evaluate(()=>__pinta({name:'<img src=x>',detail:[{id:1,quantity:1,aliment:{name:'<b>ojo</b>',calories:100}}]}));
  ck('escapa el HTML', (await p.innerHTML('#out')).includes('&lt;b&gt;ojo'), await p.innerHTML('#out'));

  ck('sin errores de JS', errs.length===0, errs);
  await b.close(); process.exit(f?1:0);
})();

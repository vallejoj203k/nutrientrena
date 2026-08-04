const { chromium } = require('../_pw');
(async()=>{
  const b=await chromium.launch(); const p=await b.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push(String(e)));
  await p.goto('file://'+__dirname+'/grupos.html');
  let f=0; const ck=(n,c,x)=>{console.log((c?'OK   ':'FALLO ')+n+(c?'':' -> '+String(JSON.stringify(x)).slice(0,220)));if(!c)f++;};

  const NOMBRES={'o1':'NutriEntrena','o2':'Centro Alfa'};
  const DATOS=[
    {id:1,title:'Dieta A1',organization_id:'o1'},
    {id:2,title:'Dieta A2',organization_id:'o1'},
    {id:3,title:'Dieta B1',organization_id:'o2'},
    {id:4,title:'Plantilla P1',organization_id:null},
  ];

  // ── Super-admin: ve varias organizaciones
  await p.evaluate(([d,n])=>__pinta(d,n),[DATOS,NOMBRES]);
  ck('hay 3 cabeceras de grupo', await p.locator('.lib-grp').count()===3, await p.locator('.lib-grp').count());
  const nombres=await p.locator('.lib-grp-nm').allTextContents();
  ck('ordenadas por nombre y plataforma al final',
     JSON.stringify(nombres)===JSON.stringify(['Centro Alfa','NutriEntrena','Catálogo de plataforma']), nombres);
  const cuentas=await p.locator('.lib-grp-n').allTextContents();
  ck('el contador de cada grupo es correcto', JSON.stringify(cuentas)===JSON.stringify(['1 dieta','2 dietas','1 dieta']), cuentas);
  ck('se ven las 4 dietas', await p.locator('tr.fila').count()===4);

  // ── Plegar un grupo
  await p.locator('.lib-grp').nth(1).click();   // NutriEntrena (2 dietas)
  await p.waitForTimeout(120);
  ck('plegar oculta solo ese grupo', await p.locator('tr.fila').count()===2, await p.locator('tr.fila').count());
  ck('la cabecera queda marcada como cerrada', await p.locator('.lib-grp.closed').count()===1);
  await p.locator('.lib-grp').nth(1).click();
  await p.waitForTimeout(120);
  ck('desplegar lo devuelve', await p.locator('tr.fila').count()===4);

  // ── Coach con UNA organización y sin plantillas: sin cabeceras
  await p.evaluate(([d,n])=>__pinta(d,n),[DATOS.filter(d=>d.organization_id==='o1'),NOMBRES]);
  ck('con un solo grupo NO se añaden cabeceras', await p.locator('.lib-grp').count()===0);
  ck('y las dietas siguen viéndose', await p.locator('tr.fila').count()===2);

  // ── Coach con su organización + plataforma: dos cajas
  await p.evaluate(([d,n])=>__pinta(d,n),[DATOS.filter(d=>d.organization_id!=='o2'),NOMBRES]);
  ck('organización + plataforma dan 2 cajas', await p.locator('.lib-grp').count()===2);
  const n2=await p.locator('.lib-grp-nm').allTextContents();
  ck('la suya primero, plataforma después', JSON.stringify(n2)===JSON.stringify(['NutriEntrena','Catálogo de plataforma']), n2);

  // ── Organización desconocida no rompe
  await p.evaluate(([d,n])=>__pinta(d,n),[[{id:9,title:'Huérfana',organization_id:'zz'},{id:10,title:'P',organization_id:null}],NOMBRES]);
  ck('una organización sin nombre no rompe', (await p.locator('.lib-grp-nm').allTextContents()).includes('Otra organización'));

  ck('sin errores de JS', errs.length===0, errs);
  await b.close(); process.exit(f?1:0);
})();

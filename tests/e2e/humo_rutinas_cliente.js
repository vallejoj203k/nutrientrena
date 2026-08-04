const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const FRONT='http://127.0.0.1:8011', API='http://127.0.0.1:8010';
const PROD='https://nutrientrena-production.up.railway.app';

(async()=>{
  const b=await chromium.launch(); const ctx=await b.newContext();
  await ctx.route(u=>u.href.startsWith(PROD), async route=>{
    const req=route.request(); const url=req.url().replace(PROD,API);
    try{ const res=await ctx.request.fetch(url,{method:req.method(),headers:req.headers(),data:req.postData()||undefined,maxRedirects:0,timeout:20000});
      const h={...res.headers()}; delete h['content-encoding']; delete h['content-length'];
      await route.fulfill({status:res.status(),headers:h,body:await res.body()});
    }catch(e){ await route.abort(); }
  });
  const p=await ctx.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(String(e)));
  let f=0; const ck=(n,c,x)=>{console.log((c?'OK   ':'FALLO ')+n+(c?'':' -> '+String(JSON.stringify(x)).slice(0,250)));if(!c)f++;};

  const SUF=String(Date.now()).slice(-6);
  const lg=await (await ctx.request.post(`${API}/api/auth/login`,{data:{email:'admin@nutrientrena.com',password:'Admin123!'}})).json();
  const token=lg.data.token, roleId=String(lg.data.user.role_id);
  const H={Authorization:'Bearer '+token};
  const post=async(path,data)=>(await ctx.request.post(`${API}/api${path}`,{data,headers:H})).json();
  const get=async(path)=>(await ctx.request.get(`${API}/api${path}`,{headers:H})).json();

  // ── Datos: ejercicio, rutina de 3 dias, cliente
  const tr=await post('/trainings',{name:'Sentadilla humo'});
  const rut=await post('/routines',{name:'Rutina de humo',days_list:[
    {day_name:'Lunes',blocks:[{block_type:'normal',order_index:0,exercises:[{training_id:tr.data.id,series:3,order_index:0}]}]},
    {day_name:'Martes',blocks:[{block_type:'normal',order_index:0,exercises:[{training_id:tr.data.id,series:4,order_index:0}]}]},
    {day_name:'Miércoles',blocks:[{block_type:'normal',order_index:0,exercises:[{training_id:tr.data.id,series:5,order_index:0}]}]}]});
  ck('rutina de prueba creada', !!rut.data?.id, rut);
  const cli=await post('/users',{name:'Cliente Humo '+SUF,email:`cliente.humo.${SUF}@nutrientrena-qa.com`,password:'Cliente123!',role_id:6});
  const clientes=await get('/users/client/findAll');
  const cd=(clientes.data||[]).find(c=>c.email===`cliente.humo.${SUF}@nutrientrena-qa.com`);
  ck('cliente de prueba creado', !!cd, String(clientes.data?.length));

  // ── A. Arrastrar días en el constructor de rutinas
  await p.goto(FRONT+'/rutinas.html');
  await p.evaluate(([t,r])=>{localStorage.setItem('token',t);localStorage.setItem('role_id',r);},[token,roleId]);
  await p.goto(FRONT+'/rutinas.html');
  await p.waitForTimeout(2500);
  await p.evaluate(id=>openForm(id), rut.data.id);
  await p.waitForTimeout(2000);
  await p.evaluate(()=>wizardNext());
  await p.waitForTimeout(800);
  const nDias=await p.locator('#daysList .day-chip').count();
  ck('el constructor pinta los 3 días', nDias===3, nDias);
  ck('los días tienen asa y contador', await p.locator('#daysList .day-grip').count()===3 && await p.locator('#daysList .day-chip-sub').count()===3);
  const g=p.locator('#daysList .day-chip').nth(0).locator('.day-grip');
  const t3=p.locator('#daysList .day-chip').nth(2);
  await g.scrollIntoViewIfNeeded(); await g.waitFor({state:'visible',timeout:8000});
  await t3.waitFor({state:'visible',timeout:8000});
  const gb=await g.boundingBox(), tb=await t3.boundingBox();
  ck('el asa es visible y arrastrable', !!gb && !!tb, {gb,tb});
  await p.mouse.move(gb.x+gb.width/2,gb.y+gb.height/2); await p.mouse.down();
  await p.mouse.move(gb.x+gb.width/2,gb.y+25,{steps:5});
  await p.mouse.move(tb.x+tb.width/2,tb.y+tb.height-4,{steps:12}); await p.mouse.up();
  await p.waitForTimeout(400);
  const orden=await p.evaluate(()=>routineData.days_list.map(d=>d.day_name));
  ck('ARRASTRAR DÍAS funciona en la app real', JSON.stringify(orden)==='["Martes","Miércoles","Lunes"]', orden);

  // ── B. Ficha del cliente: semanas, país, asignar rutina
  await p.goto(FRONT+`/client-profile.html?id=${cd.id}`);
  await p.waitForTimeout(3500);
  ck('la ficha del cliente carga', (await p.textContent('body')).includes('Cliente Humo'), '');

  // Semanas -> fecha de fin
  await p.evaluate(()=>openDatesModal());
  await p.waitForTimeout(400);
  await p.evaluate(()=>{document.getElementById('dt_start').value='2026-08-03';onStartDateInput();
                        document.getElementById('dt_weeks').value='12';onWeeksInput();});
  const fin=await p.inputValue('#dt_end');
  ck('12 SEMANAS calcula la fecha de fin', fin==='2026-10-26', fin);

  // País en editar cliente
  await p.evaluate(()=>closeDatesModal());
  await p.evaluate(()=>openEditClient());
  await p.waitForTimeout(1200);
  const nPaises=await p.locator('#ec_country_code option').count();
  ck('el selector de PAÍS existe y tiene países', nPaises>50, nPaises);

  // Asignar rutina: pantalla de carga + que aparezca el plan
  await p.evaluate(()=>closeEditClient());
  await p.evaluate(()=>showTab('entrenamiento'));
  await p.waitForTimeout(1500);
  ck('parte de "Sin plan de entrenamiento"', (await p.textContent('#entrenamientoContent')).includes('Sin plan'), '');
  await p.evaluate(()=>openAssignRoutineModal());
  await p.waitForTimeout(1500);
  await p.evaluate(id=>{selectAssignRoutine(id,document.querySelector('#aritem-'+id));}, rut.data.id);
  // Un MutationObserver no se pierde la pantalla aunque dure milisegundos,
  // y de paso mide cuánto está a la vista.
  await p.evaluate(()=>{
    window.__carga={visto:false, desde:null, ms:null};
    new MutationObserver(()=>{
      const hay=!!document.querySelector('.ent-loading-card');
      if(hay && !window.__carga.visto){window.__carga.visto=true;window.__carga.desde=performance.now();}
      if(!hay && window.__carga.desde && window.__carga.ms==null){window.__carga.ms=Math.round(performance.now()-window.__carga.desde);}
    }).observe(document.body,{childList:true,subtree:true});
  });
  await p.evaluate(()=>confirmAssignRoutine());
  await p.waitForTimeout(4000);
  const carga=await p.evaluate(()=>window.__carga);
  ck('se ve la PANTALLA DE CARGA al asignar', carga.visto, String(JSON.stringify(carga)));
  console.log('     · la pantalla de carga estuvo visible ' + carga.ms + ' ms');
  await p.waitForTimeout(4000);
  const ent=await p.textContent('#entrenamientoContent');
  ck('el plan aparece asignado', ent.includes('Rutina de humo'), ent.slice(0,150));

  ck('sin errores de JS', errs.length===0, errs);
  await b.close(); process.exit(f?1:0);
})();

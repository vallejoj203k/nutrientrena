const { chromium } = require('../_pw');
const FRONT='http://127.0.0.1:8011', API='http://127.0.0.1:8010';
const PROD='https://nutrientrena-production.up.railway.app';

(async()=>{
  const b=await chromium.launch();
  const ctx=await b.newContext();
  // El frontend apunta a produccion: se reescribe a la API local
  // No se puede continue() cambiando https->http, así que se hace la petición
  // a la API local y se devuelve la respuesta tal cual.
  await ctx.route(u=>u.href.startsWith(PROD), async route=>{
    const req=route.request();
    const url=req.url().replace(PROD, API);
    try{
      const res=await ctx.request.fetch(url,{
        method:req.method(), headers:req.headers(), data:req.postData()||undefined,
        maxRedirects:0, timeout:20000,
      });
      const body=await res.body();
      const h={...res.headers()}; delete h['content-encoding']; delete h['content-length'];
      await route.fulfill({status:res.status(), headers:h, body});
    }catch(e){ await route.abort(); }
  });
  const p=await ctx.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push(String(e)));
  let f=0; const ck=(n,c,x)=>{console.log((c?'OK   ':'FALLO ')+n+(c?'':' -> '+JSON.stringify(x).slice(0,300)));if(!c)f++;};

  // ── Login real
  const r=await ctx.request.post(`${API}/api/auth/login`,{data:{email:'admin@nutrientrena.com',password:'Admin123!'}});
  const j=await r.json();
  const token=j.data.token, roleId=String(j.data.user.role_id);
  ck('login contra la API real', !!token);

  await p.goto(FRONT+'/diets.html');
  await p.evaluate(([t,r])=>{localStorage.setItem('token',t);localStorage.setItem('role_id',r);}, [token,roleId]);

  // ── 1. Crear una dieta con 2 comidas, via API, para trabajar sobre ella
  const mk=async(path,data)=>{const res=await ctx.request.post(`${API}/api${path}`,{data,headers:{Authorization:'Bearer '+token}});return res.json();};
  const al=await mk('/aliments',{name:'Avena humo',calories:380,proteins:13,carbohydrates:67,fats:7});
  const alId=al.data.id;
  const dieta=await mk('/diets',{title:'Dieta de humo',foods:[
    {name:'Desayuno',time:'08:00',detail:[{aliment_id:alId,quantity_calc:80,order:0}]},
    {name:'Cena',time:'21:00',detail:[{aliment_id:alId,quantity_calc:50,order:0}]}]});
  const dietId=dieta.data.id;
  ck('dieta de prueba creada', !!dietId);

  // ── 2. Abrir el editor y BORRAR un alimento (el bug original)
  await p.goto(FRONT+'/diets.html');
  await p.waitForTimeout(2500);
  await p.evaluate(id=>openForm(id), dietId);
  await p.waitForTimeout(2500);
  const comidasAntes = await p.evaluate(()=>_meals.length);
  ck('el editor carga las 2 comidas', comidasAntes===2, comidasAntes);

  // borrar el unico alimento de la Cena -> comida vacia (el caso que fallaba)
  await p.evaluate(()=>{ window.confirm=()=>true; });
  const rid = await p.evaluate(()=>{const m=_meals.find(x=>x.name==='Cena');return m&&m.rows[0]?m.rows[0].id:null;});
  const mid = await p.evaluate(()=>{const m=_meals.find(x=>x.name==='Cena');return m?m.id:null;});
  await p.evaluate(([m,r])=>removeFoodRow(m,r), [mid,rid]);
  ck('la fila desaparece del estado local', await p.evaluate(()=>_meals.find(x=>x.name==='Cena').rows.length)===0);

  // ── 3. AUTOGUARDADO: no tocamos Guardar, solo esperamos
  await p.waitForTimeout(3000);
  const estado = await p.textContent('#dpAutosave').catch(()=>'');
  ck('el indicador de autoguardado dice Guardado', /Guardado/.test(estado), estado);

  const verif = await (await ctx.request.get(`${API}/api/diets/${dietId}/edit`,{headers:{Authorization:'Bearer '+token}})).json();
  const cena = (verif.data.foods||[]).find(x=>x.name==='Cena');
  ck('EL BORRADO PERSISTIO sin pulsar Guardar', cena && (cena.detail||[]).length===0, verif.data.foods);

  // ── 4. Autoguardado no duplica: forzar un segundo guardado
  await p.evaluate(()=>{document.getElementById('f_title').value='Dieta de humo (editada)';scheduleAutosave();});
  await p.waitForTimeout(3000);
  const verif2 = await (await ctx.request.get(`${API}/api/diets/${dietId}/edit`,{headers:{Authorization:'Bearer '+token}})).json();
  ck('el titulo se autoguarda', verif2.data.title==='Dieta de humo (editada)', verif2.data.title);
  ck('NO se duplicaron las comidas', (verif2.data.foods||[]).length===2, (verif2.data.foods||[]).map(x=>x.name));

  ck('sin errores de JS en diets.html', errs.length===0, errs);
  await b.close();
  process.exit(f?1:0);
})();

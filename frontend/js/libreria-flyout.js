/* El desplegable de "Librería" del menú del coach, en un solo sitio.

   Estaba copiado y pegado en 31 páginas —el comportamiento, el panel que se
   abre al lado y sus estilos— y otras dos se habían quedado con la versión
   vieja: en "Mi Organización" y en "Equipo", Librería era un enlace suelto a
   library.html, sin desplegable. Nadie se había enterado porque cada copia
   funciona por su cuenta hasta que alguien compara dos páginas.

   El módulo hace tres cosas y todas comprobando antes si hacen falta, para que
   convivan las páginas que ya lo traían con las que no:

     · pone el panel que se abre al lado, si no está;
     · pone unos estilos MÍNIMOS con :where(), que tiene especificidad cero, así
       que cualquier regla de la página gana sin discusión;
     · define openFlyout / closeFlyout / toggleLibrary.

   Las familias y sus pantallas salen de js/libreria-menu.js, que hay que cargar
   antes. */
(function () {
  function estilos() {
    if (document.getElementById('libFlyoutCss')) return;
    var s = document.createElement('style');
    s.id = 'libFlyoutCss';
    // :where() = especificidad 0. Son valores de partida para las páginas que
    // no traían estos estilos; donde ya existen, mandan los suyos.
    s.textContent =
      ':where(.nav-dropdown){display:flex;align-items:center;gap:10px;padding:10px 20px;color:#374151;' +
      'cursor:pointer;font-size:14px;border-left:3px solid transparent;user-select:none;}' +
      ':where(.nav-dropdown:hover){background:#F8FAFC;color:#4F46E5;}' +
      ':where(.nav-dropdown.open){background:linear-gradient(90deg,#EEF2FF 0%,#F5F3FF 100%);' +
      'color:#4F46E5;border-left-color:#4F46E5;font-weight:600;}' +
      ':where(.nav-chevron){margin-left:auto;flex-shrink:0;transition:transform .35s;opacity:.5;}' +
      ':where(.nav-dropdown.open .nav-chevron){transform:rotate(180deg);opacity:1;}' +
      ':where(.nav-sub){max-height:0;overflow:hidden;opacity:0;margin:0 10px;border-radius:8px;' +
      'transition:max-height .35s cubic-bezier(.4,0,.2,1),opacity .25s ease;}' +
      ':where(.nav-sub.open){max-height:240px;opacity:1;}' +
      ':where(.nav-sub-item){display:flex;align-items:center;gap:8px;padding:8px 12px 8px 14px;' +
      'color:#6B7280;font-size:12.5px;text-decoration:none;border-radius:6px;margin:2px 0;cursor:pointer;}' +
      ':where(.nav-sub-item:hover){color:#4F46E5;background:#EEF2FF;}' +
      ':where(.nav-sub-item.active){color:#4F46E5;font-weight:600;background:#EEF2FF;}' +
      ':where(.sub-arrow){margin-left:auto;opacity:.4;flex-shrink:0;}' +
      ':where(.nav-sub-item:hover .sub-arrow){opacity:1;}' +
      ':where(.flyout-item){display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:8px;' +
      'color:#374151;text-decoration:none;font-size:13.5px;cursor:pointer;}' +
      ':where(.flyout-item:hover){background:#F5F3FF;color:#4F46E5;}' +
      ':where(.flyout-item svg){opacity:.6;flex-shrink:0;}';
    document.head.appendChild(s);
  }

  function panel() {
    if (document.getElementById('flyoutPanel')) return;
    var fondo = document.createElement('div');
    fondo.id = 'flyoutBackdrop';
    fondo.setAttribute('onclick', 'closeFlyout()');
    fondo.style.cssText = 'display:none;position:fixed;inset:0;z-index:998;';

    var caja = document.createElement('div');
    caja.id = 'flyoutPanel';
    caja.style.cssText = 'display:none;position:fixed;left:244px;z-index:999;background:#fff;' +
      'border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,.12),0 2px 8px rgba(0,0,0,.08);' +
      'border:1px solid #E5E7EB;min-width:200px;overflow:hidden;transform:translateX(-8px);' +
      'opacity:0;transition:transform .25s cubic-bezier(.4,0,.2,1),opacity .2s ease;';
    caja.innerHTML =
      '<div id="flyoutHeader" style="padding:12px 16px 10px;border-bottom:1px solid #F3F4F6;' +
      'display:flex;align-items:center;gap:8px;">' +
      '<div id="flyoutDot" style="width:8px;height:8px;border-radius:50%;"></div>' +
      '<span id="flyoutTitle" style="font-size:12px;font-weight:700;color:#374151;' +
      'text-transform:uppercase;letter-spacing:.5px;"></span></div>' +
      '<div id="flyoutItems" style="padding:6px;"></div>';

    document.body.appendChild(fondo);
    document.body.appendChild(caja);
  }

  function montar() { estilos(); panel(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', montar);
  else montar();
})();

function openFlyout(e,cat){
  e.stopPropagation();
  var menu=_flyoutMenus[cat]; if(!menu) return;
  var panel=document.getElementById('flyoutPanel');
  var backdrop=document.getElementById('flyoutBackdrop');
  var rect=e.currentTarget.getBoundingClientRect();
  document.getElementById('flyoutTitle').textContent=menu.title;
  document.getElementById('flyoutDot').style.background=menu.color;
  var html='';
  menu.items.forEach(function(item){
    html+='<a class="flyout-item" href="'+item.href+'"><svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">'+item.icon+'</svg>'+item.label+'</a>';
  });
  document.getElementById('flyoutItems').innerHTML=html;
  panel.style.top=Math.min(rect.top,window.innerHeight-(menu.items.length*44+60))+'px';
  panel.style.display='block';
  backdrop.style.display='block';
  requestAnimationFrame(function(){
    panel.style.transform='translateX(0)';
    panel.style.opacity='1';
  });
}
function closeFlyout(){
  var panel=document.getElementById('flyoutPanel');
  var backdrop=document.getElementById('flyoutBackdrop');
  panel.style.transform='translateX(-8px)';
  panel.style.opacity='0';
  setTimeout(function(){panel.style.display='none';backdrop.style.display='none';},200);
}
function toggleLibrary(el){
  if(!el||typeof el==='string') el=document.getElementById('navLibrary');
  if(!el) return;
  el.classList.toggle('open');
  var sub=document.getElementById('librarySub');
  if(sub) sub.classList.toggle('open');
}
(function(){
  if(window.location.pathname.includes('library')){
    document.addEventListener('DOMContentLoaded',function(){
      var el=document.getElementById('navLibrary');
      if(el) toggleLibrary(el);
      var cat=new URLSearchParams(window.location.search).get('cat');
      if(cat) document.querySelectorAll('.nav-sub-item').forEach(function(a){
        if(a.href.includes('cat='+cat)) a.classList.add('active');
      });
    });
  }
})();

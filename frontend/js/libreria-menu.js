/* El menú de la Librería: qué familias hay y qué pantallas cuelgan de cada una.

   Estaba copiado y pegado en 31 páginas. No es una suposición: al sacarlo de
   ahí, una de las copias (contratos.html) ya se había quedado atrás —le
   faltaba "Catálogos" en Nutrición y tenía la mitad de los iconos recortados—,
   así que quien entrara por Documentos veía un menú distinto del de todos los
   demás sitios y nadie se había enterado.

   Ahora vive aquí y lo leen los dos sitios que lo necesitan: el panel del coach
   (a través de `_flyoutMenus`, que es como se llamaba, para no tocar el código
   que ya lo usaba) y el panel de plataforma, donde "Contenido global" abre
   exactamente este mismo menú. */
window.LIBRERIA_MENU = window._flyoutMenus = {
  entrenamiento:{title:'Entrenamiento',color:'#4F46E5',items:[
    {label:'Rutinas',href:'rutinas.html',icon:'<path d="M3 12h18M3 6h18M3 18h18"/>'},
    {label:'Ejercicios',href:'ejercicios.html',icon:'<circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>'},
    {label:'Grupos Musculares',href:'grupos-musculares.html',icon:'<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>'},
    {label:'Programas',href:'programas.html',icon:'<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>'}
  ]},
  nutricion:{title:'Nutrición',color:'#059669',items:[
    {label:'Dietas',href:'diets.html',icon:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'},
    {label:'Menús',href:'menus.html',icon:'<path d="M3 11l19-9-9 19-2-8-8-2z"/>'},
    {label:'Alimentos',href:'aliments.html',icon:'<path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/>'},
    {label:'Recetas',href:'recipes.html',icon:'<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>'},
    {label:'Catálogos',href:'nutrition-catalog.html',icon:'<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>'}
  ]},
  formulario:{title:'Formulario',color:'#D97706',items:[
    {label:'Check-ins',href:'forms.html?cat=checkin',icon:'<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>'},
    {label:'Onboarding',href:'forms.html?cat=onboarding',icon:'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'},
    {label:'Encuestas',href:'forms.html?cat=survey',icon:'<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>'}
  ]},
  documento:{title:'Documentos',color:'#7C3AED',items:[
    {label:'Contratos',href:'contratos.html',icon:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>'},
    {label:'Guías',href:'guias.html',icon:'<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>'},
    {label:'Plantillas',href:'plantillas.html',icon:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>'}
  ]}
};

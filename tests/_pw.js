/* Carga de Playwright, válida en los dos sitios donde corren estas pruebas.

   En CI se instala en el repositorio (`npm install playwright`), así que basta
   con require('playwright'). En el contenedor de desarrollo está instalado
   global y ese require no lo encuentra, por eso el segundo intento.

   Antes los tests requerían directamente la ruta absoluta del contenedor, así
   que pasaban en local y fallaban en CI con MODULE_NOT_FOUND. */
function cargarPlaywright() {
  try { return require('playwright'); } catch (e) {}
  for (const ruta of ['/opt/node22/lib/node_modules/playwright',
                      '/usr/lib/node_modules/playwright',
                      '/usr/local/lib/node_modules/playwright']) {
    try { return require(ruta); } catch (e) {}
  }
  throw new Error('No se encuentra Playwright. Instálalo con: npm install playwright');
}

module.exports = cargarPlaywright();

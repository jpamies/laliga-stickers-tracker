# LALIGA Stickers Tracker

Álbum estático para seguir la colección Panini LALIGA 2026-27.

**Aplicación:** https://stickers.laliga.jpamies.com/

## Funciones

- 544 cromos y variantes del checklist físico (1ª y 2ª edición), más 46 huecos
  provisionales de Últimos Fichajes y 3 de Top Fichajes.
- Cromos añadidos en la 2ª edición marcados con la etiqueta `2ª ed`, incluidos
  los números `BIS` y la sección `ÚLTIMOS FICHAJES` (UF1-UF20).
- Buscador y filtros por equipo, sección y estado, con botón para borrar la
  sección seleccionada.
- Estados `No lo tengo` y `Lo tengo`, también con clic directo en la imagen.
- Confirmación antes de retirar un cromo de la colección.
- Decisión personal `No pegar`. La recomendación automática es siempre *pegar*:
  la columna `accion` solo puede valer `PEGAR` o `ESPERAR` (huecos que Panini
  todavía no ha asignado). Nunca se descarta ni se marca para revisar un cromo
  por ti; el detalle de la comprobación queda en `estado_plantilla` y en las
  notas de cada cromo.
- Contador y vista de cromos repetidos, con el resumen de conseguidos, faltantes
  y repetidos en el título de cada sección y la fila de copias en verde cuando
  tienes un cromo y en rojo cuando está repetido.
- Progreso local sin conexión y sincronización opcional por cuenta. El progreso
  de invitado y el de cada cuenta se guardan por separado, así que iniciar
  sesión nunca sobrescribe lo que ya tienes en la nube. Para llevar el progreso
  de invitado a tu cuenta, expórtalo e impórtalo tras iniciar sesión.
- Imágenes asociadas de forma conservadora por jugador y equipo. Los cromos sin
  foto oficial se dibujan en la propia web con el escudo y la foto de
  Transfermarkt, los colores del equipo y los datos pendientes marcados.
- Estrategia de pegado basada en plantillas de Transfermarkt, siempre como
  información: la decisión de no pegar la tomas tú.
- Vista aparte con las plantillas reales de Primera División
  (`album/plantillas.html`), generada con los datos y las fotos oficiales de
  LALIGA. No está enlazada en el menú: se abre por URL directa.
- Importación y exportación del progreso.
- Importación mediante el texto de «Compartir lista» de Figuritas App, con
  revisión previa de faltantes, conseguidos y repetidos, incluidos `UF` y `TOP`,
  y un registro detallado de los números que no se han reconocido.
- Enlaces públicos revocables del álbum en modo sólo lectura.
- Amigos mediante invitación, comparación de repetidos y propuestas de intercambio.
- Sección «Amigos» con el resumen de cada amigo, acceso directo al intercambio y
  vista de su álbum en modo sólo lectura.

## Desarrollo

Regenerar los datos y el álbum:

```powershell
.\.venv\Scripts\python.exe extraer_checklist.py
.\.venv\Scripts\python.exe comprobar_plantillas.py
.\.venv\Scripts\python.exe generar_mapeo_imagenes.py
.\.venv\Scripts\python.exe generar_fotos_transfermarkt.py
.\.venv\Scripts\python.exe generar_album.py
```

`extraer_checklist.py` lee `Checklist_LALIGA_2026-27-2aED.pdf` y reutiliza los
identificadores que ya existen en `coleccion_panini.csv`, de forma que los
cromos nuevos se añaden al final de su sección sin desplazar los IDs anteriores.
El progreso del álbum se guarda por identificador, así que ese detalle es lo que
evita perderlo al publicarse una edición nueva del checklist.

`generar_fotos_transfermarkt.py` lee las plantillas ya cacheadas en
`.cache_transfermarkt/` y produce `fotos_transfermarkt.csv` con el escudo, el
dorsal y la foto de cada jugador. El álbum usa esos datos para dibujar los
cromos que todavía no tienen imagen oficial, sin copiar ninguna imagen al
repositorio.

Regenerar las plantillas reales de LALIGA y su vista:

```powershell
.\.venv\Scripts\python.exe generar_plantillas_laliga.py --refrescar
.\.venv\Scripts\python.exe generar_plantillas_html.py
```

`generar_plantillas_laliga.py` descarga los 20 equipos y sus fichas desde la API
pública de laliga.com, cachea las respuestas en `.cache_laliga/` y escribe
`laliga_equipos.csv`, `laliga_plantillas.csv` y
[`supabase/laliga_plantillas.sql`](supabase/laliga_plantillas.sql). El SQL se
regenera entero (un `delete` y los `insert` dentro de una transacción), así que
cuando LALIGA actualice dorsales o fotos basta con volver a ejecutarlo, limpiar
la tabla e importar. Las tablas viven en la migración
[`supabase/migrations/20260902120000_laliga_squads.sql`](supabase/migrations/20260902120000_laliga_squads.sql),
y hay que aplicarla antes del primer volcado.

Ejecutar las pruebas:

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

Generar el CSV maestro de estrategia con las plantillas actuales de
Transfermarkt y las altas/bajas de BeSoccer:

```powershell
.\.venv\Scripts\python.exe generar_estrategia_mercado.py `
  --refrescar-transfermarkt `
  --refrescar-besoccer `
  --progreso ruta\al\progreso.json
```

El resultado local `estrategia_mercado.csv` mantiene los cromos físicos y
añade, al final de cada club, los jugadores de su plantilla que no tienen
cromo. Las salidas confirmadas distinguen ventas, cesiones, salidas libres y
retiradas en la columna `estado_mercado`, pero `accion_estrategia` sigue siendo
`PEGAR`: el informe te dice qué ha pasado, no decide por ti. El CSV se ignora en
Git porque puede contener el progreso privado importado con `--progreso`.

La documentación sobre el manifiesto digital está en
[`PANINI_DIGITAL.md`](PANINI_DIGITAL.md), y la fuente oficial de plantillas,
dorsales y fotos de jugador en
[`ACTUALIZAR_PLANTILLAS.md`](ACTUALIZAR_PLANTILLAS.md).

## Sincronización gratuita

La web reutiliza Clerk para iniciar sesión con Google o GitHub y sincroniza el
progreso con Supabase. Si la nube no está configurada o no está disponible, el
álbum sigue funcionando con `localStorage`.

1. Crea un proyecto en Supabase Free.
2. Activa la integración de terceros de Clerk en Clerk y en Supabase.
3. Ejecuta [`supabase/schema.sql`](supabase/schema.sql) en el editor SQL de
   Supabase. La tabla tiene RLS y cada usuario sólo puede acceder a su fila.
4. Copia la URL y la clave **Publishable** del proyecto en
   [`album/cloud-config.js`](album/cloud-config.js). Esta clave es pública; no
   uses nunca una `secret` o `service_role` en el navegador.
5. Para publicar, crea una instancia de **producción** en Clerk, configura el
   dominio de GitHub Pages y usa su clave `pk_live_...`. No publiques la
   aplicación con una instancia de desarrollo `pk_test_...`.
6. Configura Supabase para confiar exclusivamente en el emisor/JWKS de esa
   instancia Clerk de producción.

Las funciones sociales se gestionan con migraciones versionadas:

```powershell
supabase link --project-ref cjwssgaigkagoocwiecq
supabase db push
```

Las invitaciones de amistad requieren confirmación expresa y caducan a los 30
días. Al caducar, iniciar sesión genera automáticamente un enlace nuevo.

La copia social contiene únicamente estado de posesión y número de copias.
`stickDecision`, el correo y los identificadores internos no se incluyen en
enlaces públicos ni comparaciones entre amigos. Las propuestas aceptadas no
modifican automáticamente el álbum: cada usuario confirma después sus copias.

Clerk Hobby y Supabase Free no requieren tarjeta para este uso. Supabase puede
pausar un proyecto gratuito tras una semana sin actividad y lo reactiva cuando
vuelve a utilizarse.

## Publicación

Cada cambio subido a la rama `main` despliega automáticamente la carpeta
`album/` mediante GitHub Pages.

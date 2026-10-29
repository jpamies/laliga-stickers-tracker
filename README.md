# LALIGA Stickers Tracker

Álbum estático para seguir la colección Panini LALIGA 2026-27.

**Aplicación:** https://stickers.laliga.jpamies.com/

## Funciones

- 661 cromos y variantes del checklist físico hasta la 4ª edición, incluidos
  los 66 Últimos Fichajes y los 3 Top Fichajes, ya todos con nombre.
- Etiquetas y filtros de `2ª ed`, `3ª ed` y `4ª ed`. La cuarta incorpora
  72 cromos: 37 variantes de equipos, UF41-UF66, los 3 Top Fichajes y
  6 Extra Sticker (Rodri y Bellingham en bronce, plata y oro).
- Buscador y filtros por equipo, sección y estado, con botón para borrar la
  sección seleccionada.
- Estados `No lo tengo` y `Lo tengo`, también con clic directo en la imagen.
- Confirmación antes de retirar un cromo de la colección.
- Decisión personal `No pegar`. La recomendación pública es siempre *pegar*:
  la columna `accion` solo puede valer `PEGAR` o `ESPERAR` (huecos que Panini
  todavía no ha asignado). Nunca se descarta ni se marca para revisar un cromo
  por ti; el detalle de la comprobación queda en `estado_plantilla` y en las
  notas de cada cromo.
- Las 44 filas rojas del checklist de 4ª edición se conservan como
  `baja_panini`: son bajas indicadas por Panini, usadas en la optimización
  y en la comprobación para evitar confundir a dos jugadores con el mismo
  apellido. No cambian las decisiones personales ni la acción pública `PEGAR`.
- Sugerencia privada de `No pegar` para los jugadores que ya no aparecen en la
  plantilla oficial de LALIGA. Solo la ve la cuenta dueña del álbum: para el
  resto de visitantes, para los enlaces públicos y al mirar el álbum de un
  amigo, la vista no cambia.
- Contador y vista de cromos repetidos, con el resumen de conseguidos, faltantes
  y repetidos en el título de cada sección y la fila de copias en verde cuando
  tienes un cromo y en rojo cuando está repetido. Los números van en verde (los
  tengo), rojo (me faltan), ámbar (repetidos) y gris (los que no pegas).
- Los cromos marcados `No pegar` salen del objetivo del álbum: no cuentan en el
  progreso ni como pendientes, y se resumen aparte.
- Filtros por edición y un interruptor para ocultar los cromos que no vas a
  pegar. Cada cromo lleva la etiqueta de la edición en que se anunció, con un
  color por edición, y se puede filtrar por ella o buscarla por texto.
- Minutos de juego en la ficha de cada cromo: minutos, partidos y goles o
  asistencias, tomados de las estadísticas oficiales de LALIGA. El número va en
  verde para un titular, ámbar para un jugador de rotación y rojo cuando no ha
  disputado un solo minuto, que es la señal más clara para decidir entre la
  variante A y la B. Viajan en una tabla aparte indexada por cromo, así que sólo
  añaden 12 KB al álbum.
- Interruptor `Fichas`/`Lista`/`Intercambio`. La lista cambia las fotos por una
  fila por cromo con el escudo del equipo, el número y el nombre, así que una
  plantilla entera cabe de un vistazo cuando vas a hacer cambios. El número
  lleva el mismo código de color que los contadores de sección y la fila sigue
  permitiendo marcar el cromo y contar copias. Se combina con el resto: `Lista`
  más `Sin conseguir` da lo que buscas, y `Lista` dentro de `Repetidos` lo que
  ofreces. La elección se recuerda entre visitas y la lista también sale bien
  impresa.
- El modo `Intercambio` aprieta todavía más: escudo y número en una chapa de
  22 píxeles de alto, sin cabeceras de sección porque el escudo ya dice de qué
  equipo es. Los 661 cromos se muestran de forma compacta. Tocar una chapa no
  cambia nada: abre un globo con el nombre del jugador, la sección y los
  botones `−` y `+`, que se queda abierto para encadenar varias copias. Así el
  nombre se lee también en el móvil, donde no hay ratón que enseñe el tooltip,
  y ningún clic suelto toca el álbum. Se cierra con `Esc`, con la `×` o tocando
  fuera. En el móvil las chapas crecen hasta los 40 píxeles para que el dedo no
  se equivoque de cromo. Los Extra Sticker, que no llevan número, se muestran
  por el nombre del jugador.
- Modo catálogo sin login: si no inicias sesión, el álbum se abre sin marcas y
  sólo deja consultar la colección completa. Para ver y editar tu progreso hay
  que entrar con cuenta, y entonces se carga únicamente el álbum de la nube.
- Los cromos de 2ª, 3ª y 4ª edición usan exclusivamente el retrato oficial
  de LALIGA, con el escudo y los colores del equipo. No se muestran imágenes
  Panini ni retratos de Transfermarkt para estas ediciones; si no hay una foto
  oficial fiable se dibuja una silueta.
  Los de 1ª edición conservan las imágenes Panini disponibles. Cuando no las
  hay, se dibujan con el retrato de LALIGA, ampliado hasta un encuadre parecido
  al de un cromo real; Transfermarkt queda como alternativa sólo para esta
  primera edición, y si tampoco hay foto se usa una silueta.
  Los retratos de LALIGA usan un zoom `×2,44`, el doble del encuadre anterior
  (`×1,22`). Se centran horizontalmente y se elevan hacia el borde superior,
  ampliando el recorte por arriba sin cambiar el tamaño de la cara. Así quedan
  visibles la cabeza y los hombros, en vez de cortar el retrato por el cuello. El
  recorte no afecta al escudo, el nombre ni las imágenes Panini o Transfermarkt.
  Los nombres cortos ambiguos se resuelven por identidad: «Junior» es Júnior
  Firpo y «Rodri» es Rodrigo Hernández Cascante, no Luiz Júnior ni Rodri Mendoza.
  Si el catálogo digital no incluye al jugador correcto se usa su retrato oficial.
  Los cromos generados de secciones especiales (UF, Top Fichajes, Extra Sticker,
  etc.) muestran el escudo del club del jugador en lugar de las siglas de la
  sección, con el nombre del equipo al pasar el ratón y en la descripción
  accesible. Se mantienen el número y la sección originales. Si no hay un club
  o escudo conocido se conserva el identificador de sección.
- Estrategia de pegado basada en plantillas de Transfermarkt, siempre como
  información: la decisión de no pegar la tomas tú.
- Ficha oficial de LALIGA en cada cromo (nombre completo, dorsal y
  demarcación), con un guion cuando el jugador ya no está en el club.
- Vista aparte con las plantillas reales de Primera División
  (`album/plantillas.html`), generada con los datos y las fotos oficiales de
  LALIGA, incluido el cromo del álbum que representa a cada jugador. No está
  enlazada en el menú: se abre por URL directa.
- Importación y exportación del progreso.
- Importación mediante el texto de «Compartir lista» de Figuritas App, con
  revisión previa de faltantes, conseguidos y repetidos, incluidos `UF` y `TOP`,
  y un registro detallado de los números que no se han reconocido.
  Los BIS compartidos por dos jugadores (Celta y Deportivo, `14BIS`) se
  conservan sin cambios y se notifican para revisarlos a mano.
- Enlaces públicos revocables del álbum en modo sólo lectura.
- En «Compartir», listas de faltantes, repetidos o ambas para copiar y pegar
  en WhatsApp, sin que quien las recibe necesite usar la web. El texto se agrupa
  por equipo/sección, excluye tus «No pegar» de los faltantes y expresa los
  repetidos en copias sobrantes (`×N`), conservando una para ti. Los BIS
  compartidos se distinguen por jugador y edición; los Extra Sticker, por nombre.
  Se comparte todo tu álbum, no sólo el filtro de pantalla. El móvil puede
  ofrecer «Compartir texto…» para elegir WhatsApp u otra aplicación; copiar
  sigue disponible en los demás navegadores. No se envía nada automáticamente
  ni se incluyen decisiones privadas, identificadores o enlaces en el texto.
- Amigos mediante invitación, comparación de repetidos y propuestas de intercambio.
- En los intercambios, «Te puede dar» y sus contadores excluyen los cromos que
  tu álbum considera «No pegar», incluida la sugerencia privada de jugadores
  fuera de plantilla. Si eliges «Pegar» expresamente, vuelven a incluirse.
  Esto no cambia lo que puedes ofrecer ni comparte tus decisiones privadas.
- Sección «Amigos» con el resumen de cada amigo, acceso directo al intercambio y
  vista de su álbum en modo sólo lectura.
- Intercambio grupal desde «Propuestas» o «Amigos»: selecciona los participantes
  y calcula un plan de reparto que maximiza los cromos transferidos, también en
  ciclos entre tres o más personas, con saldo 1:1 por participante.

## Desarrollo

Para abrir la web local, ejecuta la tarea de VS Code **Web local (album)** o:

```powershell
.\.venv\Scripts\python.exe -m http.server 8000 --bind 127.0.0.1 --directory album
```

La aplicación estará en http://127.0.0.1:8000/. Se sirven directamente los
archivos de `album/`, sin build. La clave de producción de Clerk sólo admite
el dominio publicado: para probar autenticación en localhost hace falta una
instancia de desarrollo y su integración correspondiente con Supabase.

Regenerar los datos y el álbum:

```powershell
.\.venv\Scripts\python.exe extraer_checklist.py
.\.venv\Scripts\python.exe comprobar_plantillas.py
.\.venv\Scripts\python.exe generar_plantillas_laliga.py --refrescar
.\.venv\Scripts\python.exe comprobar_plantillas_laliga.py
.\.venv\Scripts\python.exe generar_mapeo_imagenes.py
.\.venv\Scripts\python.exe generar_fotos_transfermarkt.py
.\.venv\Scripts\python.exe generar_estadisticas_laliga.py --refrescar
.\.venv\Scripts\python.exe generar_album.py
.\.venv\Scripts\python.exe analizar_optimizacion.py
```

`generar_album.py` necesita `laliga_estadisticas.csv` para los minutos de cada
ficha; si el archivo no está, el álbum se genera igual pero sin esa fila.

`extraer_checklist.py` lee por defecto `Checklist_LALIGA_2026-27-4aED.pdf`. Ese
documento no se versiona, pero sí todo lo que sale de él, así que el resto del
proceso funciona sin tenerlo. En
[TERCERA_EDICION.md](TERCERA_EDICION.md) están las diferencias que trajo esa
edición, incluidas las dos erratas del checklist que se corrigen al extraerlo.

El extractor reutiliza los identificadores que ya existen en
`coleccion_panini.csv`, sin desplazar los IDs anteriores. Los 29 huecos
provisionales de UF41-UF66 y Top Fichajes también conservan su identificador.
Cuando dos cromos comparten número BIS se distinguen por su repetición en
el checklist: Casadó no sustituye al ID de Gijselhart ni Burcio al de Vecino.
El progreso del álbum se guarda por identificador, así que ese detalle es lo que
evita perderlo al publicarse una edición nueva del checklist.

La cuarta edición marca en rojo el fondo de las filas de las bajas. El
extractor lee las celdas individuales, no el rectángulo de un trazado que puede
agrupar filas separadas. Tampoco basta con leer el color de la letra: es negro.
Los clubes omitidos en UF41-UF66 y Top Fichajes están contrastados con las
plantillas oficiales actuales en `UNLABELLED_SIGNINGS`, con el nombre como
comprobación para no reutilizar el dato si Panini cambia el jugador.
El PDF corrige Mariano (Alavés 20BIS) a `3ª ed`, de modo que esa edición pasa
de 51 a 52 etiquetas sin añadir ni cambiar su cromo.

`generar_fotos_transfermarkt.py` lee las plantillas ya cacheadas en
`.cache_transfermarkt/` y produce `fotos_transfermarkt.csv` con el escudo, el
dorsal y la foto de cada jugador. El álbum usa esos datos para dibujar los
cromos que todavía no tienen imagen oficial, sin copiar ninguna imagen al
repositorio.

`comprobar_plantillas_laliga.py` cruza el checklist con `laliga_plantillas.csv`
y aprovecha el mismo recorrido para escribir los dos índices:

- `comprobacion_laliga.csv`, por identificador de cromo, con el estado de cada
  jugador (`en_plantilla`, `fuera_plantilla`, `coincidencia_dudosa`…) y su
  ficha oficial.
- las columnas `cromo_id`, `cromo_seccion`, `cromo_numero`, `cromo_nombre` y
  `cromos` que devuelve a `laliga_plantillas.csv` y al SQL, para saber qué
  cromo representa a cada jugador de la plantilla real. Sólo se cruzan las
  secciones de equipo, Últimos y Top Fichajes; las temáticas (ADN, Fantasy, Draft y
  Extra Sticker) repiten jugadores con otro diseño y quedan fuera.

El emparejamiento es deliberadamente conservador: ante un nombre corto, un
apellido compartido o un parecido razonable prefiere `coincidencia_dudosa`
antes que afirmar que alguien se ha ido.

En la ficha de cada cromo el álbum muestra los datos oficiales de LALIGA
(nombre completo, dorsal y demarcación) en lugar de la coincidencia de
Transfermarkt, y un guion cuando el jugador ya no está en el club o el
emparejamiento no es firme.

`generar_plantillas_markdown.py` vuelca lo mismo a
[`PLANTILLAS_LALIGA.md`](PLANTILLAS_LALIGA.md), para poder consultar sin abrir
la hoja de cálculo quién está registrado en cada club, con qué dorsal y qué
cromo le corresponde. Empieza con el total de jugadores registrados y el
reparto por demarcación y por equipo.

### Sugerencia privada de «no pegar»

`comprobacion_laliga.csv` viaja al álbum como el campo `estado_laliga` de cada
cromo, pero la recomendación pública sigue siendo `PEGAR` para todos. Solo la
cuenta dueña del álbum ve la pastilla `NO PEGAR` y el pie «Ya no está en el
club» en los cromos con `fuera_plantilla`, y esos cromos entran en el filtro
«No pegar».

La comprobación se hace en el navegador contra `strategyOwnerHash` de
[`album/cloud-config.js`](album/cloud-config.js), que guarda el **SHA-256** del
identificador de la cuenta para no publicarlo. Para cambiar de cuenta:

```powershell
.\.venv\Scripts\python.exe -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())" user_XXXXXXXX
```

La sugerencia se desactiva en los enlaces públicos de sólo lectura y al mirar
el álbum de un amigo. Es una preferencia de visualización, no un secreto: el
campo `estado_laliga` está en el HTML público porque procede del catálogo
abierto de LALIGA. Lo que nunca se comparte es tu decisión personal
`stickDecision`.

Regenerar las plantillas reales de LALIGA y su vista:

```powershell
.\.venv\Scripts\python.exe generar_plantillas_laliga.py --refrescar
.\.venv\Scripts\python.exe comprobar_plantillas_laliga.py
.\.venv\Scripts\python.exe generar_plantillas_markdown.py
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

Pruebas de comportamiento de los intercambios y su optimizador (con Node.js):

```powershell
node --test test_social.js test_pool_optimizer.js
```

El optimizador se contrasta con enumeración exhaustiva de inventarios pequeños
y con casos de tamaño equivalente al álbum completo.

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
[`PANINI_DIGITAL.md`](PANINI_DIGITAL.md), la fuente oficial de plantillas,
dorsales y fotos de jugador en
[`ACTUALIZAR_PLANTILLAS.md`](ACTUALIZAR_PLANTILLAS.md), las plantillas ya
descargadas en [`PLANTILLAS_LALIGA.md`](PLANTILLAS_LALIGA.md), y el análisis de
qué página de equipo se puede completar sin pegar jugadores que ya se fueron en
[`OPTIMIZACION_PLANTILLAS.md`](OPTIMIZACION_PLANTILLAS.md).

### Optimización de la página de cada equipo

```powershell
.\.venv\Scripts\python.exe generar_estadisticas_laliga.py --refrescar
.\.venv\Scripts\python.exe analizar_optimizacion.py
```

Cada club ocupa 20 huecos: escudo, entrenador y 18 jugadores, algunos con dos
variantes (`A`/`B` o `BIS`) de las que sólo se pega una.
`generar_estadisticas_laliga.py` descarga los minutos de cada jugador y
`analizar_optimizacion.py` los cruza con el checklist para escribir
[`OPTIMIZACION_PLANTILLAS.md`](OPTIMIZACION_PLANTILLAS.md), que por equipo
responde a tres cosas: qué huecos se han quedado sin nadie del club, cuál de
las dos variantes conviene pegar cuando ambas siguen en plantilla, y qué
jugadores inscritos sin cromo se lo han ganado a base de minutos.

Los Últimos Fichajes no entran en ese recuento: se pegan en su propia sección,
no tapando huecos de equipo. Tampoco los Top Fichajes. El informe etiqueta
también la 3ª y la 4ª edición y excluye las bajas marcadas por Panini de las
variantes recomendadas, sin convertirlas en decisiones personales del álbum.

## Sincronización gratuita

La web reutiliza Clerk para iniciar sesión con Google o GitHub y sincroniza el
progreso con Supabase. Con la nube configurada, sin login se muestra sólo el
catálogo (sin progreso); al iniciar sesión se carga y se edita el álbum de esa
cuenta en Supabase. Si la nube no está configurada o no está disponible, el
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

Una migración aplicada no se vuelve a ejecutar: si necesitas cambiar una tabla,
añade un fichero nuevo en `supabase/migrations/` en lugar de editar el que la
creó, o las bases de datos existentes se quedarán sin ese cambio.

Las invitaciones de amistad requieren confirmación expresa y caducan a los 30
días. Al abrir una invitación sin sesión, el cuadro ofrece «Iniciar sesión» y
«Registrarse» para entrar directamente al flujo de Clerk; al caducar, iniciar
sesión genera automáticamente un enlace nuevo.

La copia social contiene únicamente estado de posesión y número de copias.
`stickDecision`, el correo y los identificadores internos no se incluyen en
enlaces públicos ni comparaciones entre amigos. Esa copia
(`album_social_progress`) la deriva un disparador desde `album_progress`, así
que no puede quedarse obsoleta aunque el álbum se reinicie desde el panel de
Supabase o desde otro dispositivo. Las propuestas aceptadas no modifican
automáticamente el álbum: cada usuario confirma después sus copias.

### Intercambio grupal

Abre «Crear Intercambio Grupal» desde «Amigos» o «Propuestas», o la pestaña
«Grupal» del cuadro de intercambios. Tú participas siempre y puedes elegir uno
o varios amigos. No necesitan ser amigos entre sí: sólo se usan inventarios que
ya puedes consultar. Al calcular se vuelven a obtener sus colecciones.

- Cada cromo ofrece como máximo `copias - 1`: nadie entrega su última copia.
- Cada participante sólo recibe cromos que le faltan, una copia de cada uno y
  nunca una copia aportada por él mismo.
- **Sólo las copias entregadas a otra persona generan saldo.** Los repetidos
  que quedan sin usar no dan crédito. Como no hay saldo externo, al completar
  el reparto todos aportan exactamente lo mismo que reciben, aunque sus
  entregas y recogidas sean con personas distintas. Primero se depositan las
  aportaciones indicadas y después se reparten.
- Se excluyen tus «No pegar», tanto manuales como sugeridos, respetando «Pegar»
  explícito. Las decisiones privadas de tus amigos no se consultan ni se
  comparten: sus faltas se deducen de la posesión.

El grafo es una **circulación integral** entre participantes y tipos de cromo.
La conservación del flujo impone el saldo 1:1 y las capacidades respetan las
copias disponibles y las faltas. El objetivo principal es el número total de
copias que cambian de dueño, no el de parejas ni el de propuestas.
Se resuelve como flujo de coste mínimo con potenciales de Dijkstra y flujos
bloqueantes de **Dinic** en la red residual. Los costes usan `BigInt` para que
la cantidad de transferencias tenga prioridad exacta sobre cualquier desempate.
Entre planes con el mismo máximo se priorizan los cromos con un único receptor
posible; después se comparan las aportaciones útiles que desbloquea cada
receptor, el total de sus repetidos y el avance de su álbum. Los empates finales
son deterministas. Estas prioridades nunca sacrifican el máximo: una asignación
local irreversible podría impedir un ciclo más largo.

El cálculo se ejecuta en un Web Worker para no bloquear la interfaz. Se puede
cancelar y sólo se presenta como óptimo cuando termina. Cambiar participantes,
cambiar tu progreso, cerrar el cuadro o cambiar de sesión invalida el plan o
cancela el cálculo pendiente.

El resultado muestra aportaciones, recepciones, saldo y entregas por pareja, y
se puede descargar como texto para compartirlo. **No reserva copias, no envía
propuestas ni modifica los álbumes**, `localStorage` o las tablas de Supabase.
Es una foto de los inventarios consultados: si alguien cambia su colección hay
que recalcular. No requiere migraciones.

Clerk Hobby y Supabase Free no requieren tarjeta para este uso. Supabase puede
pausar un proyecto gratuito tras una semana sin actividad y lo reactiva cuando
vuelve a utilizarse.

## Publicación

Cada cambio subido a la rama `main` despliega automáticamente la carpeta
`album/` mediante GitHub Pages.

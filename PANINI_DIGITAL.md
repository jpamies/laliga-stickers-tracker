# Panini Digital Collections: extracción de datos e imágenes

Documentación técnica para actualizar en el futuro los datos de la colección
**LALIGA EA SPORTS 2026/2027** usados por este proyecto.

Última comprobación: **2026-08-24**.

## Resumen

La aplicación de Panini está disponible en:

- Web: <https://www.paninidigitalcollections.com/app>
- CDN: <https://assets.paninidigitalcollections.com>

La aplicación web carga un juego desarrollado con **Unity WebGL**. La información
de las colecciones no está escrita directamente en el HTML: Unity descarga un
manifiesto JSON y guarda una copia en IndexedDB.

La colección actual de LALIGA 2026/27 tiene:

- ID de colección: `22`
- Nombre: `LALIGA EA SPORTS 2026/2027`
- Estado: `active`
- Fecha de caducidad: `2027-06-30T23:59:59Z`
- Cromos digitales: `477`
- Páginas digitales: `68`
- Imágenes HQ disponibles: `true`

La copia del manifiesto obtenida el 2026-08-24 está guardada en
[`panini_digital_collection_22.json`](panini_digital_collection_22.json).

## Procedimiento recomendado para actualizar

No se debe guardar como permanente la URL versionada actual del catálogo porque
Panini puede cambiar el sufijo cuando publique nuevos cromos.

### 1. Consultar el manifiesto principal

Abrir:

<https://www.paninidigitalcollections.com/manifest/assets>

La respuesta contiene una entrada similar a:

```json
{
  "statics": {
    "config/collections.json": {
      "url": "https://www.paninidigitalcollections.com/manifest/collections-1786442998",
      "loading": "prefetch"
    }
  }
}
```

Hay que usar siempre el valor actual de:

```text
statics["config/collections.json"].url
```

El número final, como `1786442998`, es versionado y puede cambiar.

### 2. Descargar el catálogo versionado

En la comprobación del 2026-08-24, la URL era:

<https://www.paninidigitalcollections.com/manifest/collections-1786442998>

Ejemplo en PowerShell:

```powershell
$assets = Invoke-RestMethod `
  -Uri "https://www.paninidigitalcollections.com/manifest/assets"

$collectionsUrl = $assets.statics."config/collections.json".url
$manifest = Invoke-RestMethod -Uri $collectionsUrl

$collection = $manifest.collections |
  Where-Object { $_.id -eq 22 }

$collection |
  ConvertTo-Json -Depth 20 |
  Set-Content -Encoding utf8 "panini_digital_collection_22.json"
```

Ejemplo equivalente en Python:

```python
import json
from pathlib import Path

import requests

assets = requests.get(
    "https://www.paninidigitalcollections.com/manifest/assets",
    timeout=30,
).json()

collections_url = assets["statics"]["config/collections.json"]["url"]
manifest = requests.get(collections_url, timeout=30).json()
collection = next(
    item for item in manifest["collections"] if item["id"] == 22
)

Path("panini_digital_collection_22.json").write_text(
    json.dumps(collection, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
```

### 3. Comprobar si Panini ha añadido cromos

Revisar estos campos:

```python
collection["content"]["num_stickers"]
len(collection["stickers"])
collection["content"]["num_pages"]
len(collection["pages"])
```

El 2026-08-24, los resultados esperados eran:

```text
num_stickers = 477
len(stickers) = 477
num_pages = 68
len(pages) = 68
```

También conviene comparar:

- IDs que no estaban en la copia anterior.
- URLs de imagen que hayan cambiado.
- Nuevos grupos o secciones.
- Nuevas páginas o slots.
- Cambios en etiquetas de jugadores.

## Estructura de los datos

La raíz del manifiesto contiene:

```text
collections
```

Cada colección incluye, entre otros:

```text
id
name
description
expires_at
status
category
content
assets
packs
swaps
stickers
groups
pages
ecommerce
buy_missing_stickers
rankings
```

### Cromos

Cada elemento de `collection["stickers"]` tiene esta estructura:

```json
{
  "id": 8511,
  "label": "PAU CUBARSÍ",
  "number": 4,
  "image_url": "https://assets.paninidigitalcollections.com/assets/22/stickers/134-afd7625f8db2f6768d66e4ab0725393d68118964.png",
  "group_id": 665,
  "slot_id": 8511
}
```

Algunos cromos contienen también:

```json
{
  "rotated": true
}
```

Significado de los campos:

- `id`: identificador interno del cromo en Panini.
- `label`: nombre o descripción.
- `number`: número dentro de su grupo o sección digital.
- `image_url`: URL completa de la imagen normal.
- `group_id`: identificador de la sección digital.
- `slot_id`: hueco del álbum digital.
- `rotated`: indica que la imagen se muestra girada.

El número que aparece en el nombre del archivo de imagen es el índice global del
recurso digital. No es necesariamente igual a `number`.

Ejemplo:

```text
Cubarsí:
number del grupo = 4
índice global de la imagen = 134
```

### Grupos

`collection["groups"]` relaciona cada `group_id` con su nombre:

```json
{
  "id": 665,
  "label": "FC BARCELONA"
}
```

### Páginas y slots

`collection["pages"]` contiene:

- ID y número de página.
- URL del fondo de la página.
- Slots donde se colocan los cromos.

Estos datos permiten reconstruir el orden del álbum digital, pero el orden y los
números no coinciden necesariamente con el checklist físico.

## Patrón de las imágenes normales

Las imágenes normales siguen este formato:

```text
https://assets.paninidigitalcollections.com/assets/{collection_id}/stickers/{indice_global}-{hash}.png
```

Ejemplos:

```text
Gerard Martín:
https://assets.paninidigitalcollections.com/assets/22/stickers/133-b69b6e99f6171e473b3f4961f4cc7129d2ba4a61.png

Pau Cubarsí:
https://assets.paninidigitalcollections.com/assets/22/stickers/134-afd7625f8db2f6768d66e4ab0725393d68118964.png
```

Las imágenes normales comprobadas miden `232 x 308` píxeles.

El sufijo tiene 40 caracteres hexadecimales, pero no coincide con:

- SHA-1 del PNG servido por el CDN.
- MD5 del PNG.
- Número del cromo.
- Nombre del jugador.
- Combinaciones sencillas de número, nombre y ruta.

No se debe intentar generar el hash. La fuente fiable es siempre `image_url` en
el manifiesto.

## Imágenes HQ

Las imágenes HQ siguen este formato:

```text
https://assets.paninidigitalcollections.com/assets/{collection_id}/hq_stickers/{indice_global}-{hash_hq}.png
```

Ejemplo comprobado:

```text
Gerard Martín:
https://assets.paninidigitalcollections.com/assets/22/hq_stickers/133-3d48cc09089fed7cb1f24de0902d0dd4645a54d1.png

Pau Cubarsí:
https://assets.paninidigitalcollections.com/assets/22/hq_stickers/134-c60ed75dfe472821732974e5cd2ddcb71563a50f.png
```

La versión HQ de Cubarsí mide `464 x 616` píxeles, exactamente el doble que la
normal en cada dimensión.

El catálogo público:

- Indica `"hq_stickers": true`.
- No incluye las URLs HQ completas.
- No incluye el hash HQ.

También se comprobó que:

- Sustituir `stickers` por `hq_stickers` conservando el hash normal devuelve
  `404`.
- Usar el hash HQ en la carpeta normal devuelve `404`.
- Pedir únicamente `{indice_global}.png` devuelve `404`.

Por tanto, el hash normal y el hash HQ son independientes.

Unity solicita la URL HQ cuando el usuario abre el detalle de un cromo. Si se
necesitan todas las HQ, será necesario localizar la respuesta que entrega esas
URLs o registrar las peticiones de red al abrir los cromos. No se deben intentar
adivinar hashes por fuerza bruta.

Durante la comprobación se localizó la petición que entrega el detalle:

```text
POST /api/v1/album/sticker_details.json?locale=en
```

La respuesta incluye la URL HQ completa del cromo abierto. Este endpoint requiere
la autorización de la sesión de Unity y, en las pruebas realizadas, sólo devolvió
el detalle del cromo seleccionado. No proporciona un índice público con las 477
URLs HQ.

## Funcionamiento de la aplicación Unity

La página `/app` contiene:

```html
<div id="page-game">
  <!-- React carga aquí Unity WebGL -->
</div>
```

El canvas usado durante la comprobación fue:

```html
<canvas
  id="react-unity-webgl-canvas-1"
  class="unity__instance">
</canvas>
```

Durante el arranque, Unity realiza, entre otras, estas peticiones:

```text
POST /api/v1/boot/version.json
POST /api/v1/boot/config.json
POST /api/v1/auth/login/token.json
POST /api/v1/account/profile/status.json
POST /api/v1/game/init.json
POST /api/v1/collections/overview.json
GET  /manifest/assets
```

Las peticiones de cuenta y autenticación no son necesarias para descargar el
manifiesto público. No se deben guardar tokens, cookies ni datos de sesión.

## Copia de Unity en IndexedDB

Unity guarda una copia del catálogo en IndexedDB:

```text
Base de datos: /idbfs
Object store: FILE_DATA
```

En la comprobación del 2026-08-24, la clave era:

```text
/idbfs/0e96aa3fe1ae43785613ec99ba55598b/assets/collections-1786442998
```

La parte intermedia y la versión final pueden cambiar.

El registro contenía:

- Un JSON válido.
- Aproximadamente 131 KB sin formatear.
- Las 477 URLs normales de la colección 22.
- Ninguna URL `hq_stickers`.

Esta copia permitió descubrir el manifiesto, pero para actualizaciones futuras
es más sencillo y estable consultar `/manifest/assets`.

## Relación con el álbum físico

La colección digital contiene 477 cromos, mientras que el CSV de este proyecto
contiene 514 entradas y variantes físicas.

No se deben relacionar únicamente por número porque:

- El número de la URL es global dentro de la colección digital.
- `number` es local al grupo digital.
- El checklist físico usa números por equipo y variantes A/B.
- Hay cromos y secciones especiales que pueden diferir.

La relación debe hacerse principalmente mediante:

1. Nombre normalizado.
2. Equipo o grupo.
3. Tipo de cromo.
4. Revisión manual de coincidencias ambiguas.

## Integración actual con el álbum HTML

El script [`generar_mapeo_imagenes.py`](generar_mapeo_imagenes.py) realiza la
unión conservadora entre el checklist físico y el manifiesto digital:

```powershell
.\.venv\Scripts\python.exe generar_mapeo_imagenes.py
.\.venv\Scripts\python.exe generar_album.py
```

El resultado se guarda en [`imagenes_panini.csv`](imagenes_panini.csv) e incluye:

- ID del cromo físico.
- URL de imagen digital.
- ID interno e índice global digital.
- Etiqueta y grupo digital.
- Método de coincidencia.
- Confianza y notas.

Estado de la unión comprobada el 2026-08-24:

```text
398 entradas físicas con una imagen digital segura
20 escudos obtenidos desde Transfermarkt
96 entradas sin imagen
514 entradas físicas totales
```

Los casos sin coincidencia segura permanecen deliberadamente sin imagen. No se
usan números para asociar cromos y no se aceptan coincidencias de jugadores de
otro club. Por ejemplo, `Mendy` del Real Madrid no se asocia con `Nobel Mendy`
del Rayo Vallecano.

En el álbum:

- `No lo tengo`: imagen en escala de grises.
- `Lo tengo`: imagen en color.
- `Pegado`: imagen en color.
- Sin coincidencia digital: marcador `Imagen no disponible`.

El manifiesto de Panini no publica los escudos como recursos independientes;
aparecen integrados en los fondos de página. Para los 20 cromos `Escudo`, el
mapa usa los PNG de los clubes publicados por Transfermarkt y los identifica con
el método `escudo_transfermarkt`.

## Recomendaciones

- Conservar una copia fechada del manifiesto antes de actualizar.
- Comparar los manifiestos viejo y nuevo por `id` e `image_url`.
- No asumir que el ID de colección seguirá siendo `22` en otra temporada.
- Buscar la colección por `id` y validar también su `name`.
- No almacenar credenciales ni tokens del navegador.
- Evitar descargar repetidamente las 477 imágenes.
- Considerar que Panini puede cambiar o retirar las URLs cuando finalice la
  colección.
- Revisar las condiciones de uso de Panini antes de publicar o redistribuir sus
  imágenes.

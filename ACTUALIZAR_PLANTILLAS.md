# Actualización de plantillas desde LALIGA

Fuente oficial para refrescar plantillas, dorsales y fotos de jugador. Sustituye
o complementa a Transfermarkt, que se sigue usando para escudos y para detectar
salidas.

## Resumen

| Dato | Valor |
| --- | --- |
| Host | `https://apim.laliga.com/public-service/api/v1` |
| Clave pública | `c13c3a8e2f6b46da9c5c425cf61fab3e` |
| Temporada | `seasonYear=2026` |
| Competición | `laliga-easports-2026` |
| Equipos | 20 |
| Jugadores | 560 |
| Comprobado | 2026-09-02 |

La clave `subscription-key` viaja en la URL del sitio público
[laliga.com](https://www.laliga.com/es-GB/laliga-easports/clubes), así que no es
un secreto, pero puede rotar sin aviso. Si las peticiones empiezan a devolver
`401`, hay que volver a leerla desde la web.

## Listado de equipos

El endpoint general de equipos devuelve 244 clubes de todo el mundo. Para
quedarse sólo con LALIGA EA SPORTS hay que filtrar por competición:

```
GET /teams?subscriptionSlug=laliga-easports-2026&limit=30&contentLanguage=es&subscription-key=<clave>
```

Los identificadores de competición salen de:

```
GET /subscriptions?contentLanguage=es&subscription-key=<clave>
```

Filtros que **no** funcionan: `competitionId`, `competition`,
`/subscriptions/<slug>/teams` y `/competitions/<slug>/teams`.

## Plantilla de un equipo

```
GET /teams/<slug>/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=<clave>
```

### URLs de los 20 equipos

| Sección del álbum | Slug | Jugadores |
| --- | --- | --- |
| DEPORTIVO ALAVÉS | [`d-alaves`](https://apim.laliga.com/public-service/api/v1/teams/d-alaves/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 26 |
| ATHLETIC CLUB DE BILBAO | [`athletic-club`](https://apim.laliga.com/public-service/api/v1/teams/athletic-club/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 26 |
| ATLÉTICO DE MADRID | [`atletico-de-madrid`](https://apim.laliga.com/public-service/api/v1/teams/atletico-de-madrid/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 27 |
| FC BARCELONA | [`fc-barcelona`](https://apim.laliga.com/public-service/api/v1/teams/fc-barcelona/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 29 |
| REAL BETIS | [`real-betis`](https://apim.laliga.com/public-service/api/v1/teams/real-betis/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 26 |
| RC CELTA DE VIGO | [`rc-celta`](https://apim.laliga.com/public-service/api/v1/teams/rc-celta/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 27 |
| DEPORTIVO | [`rc-deportivo`](https://apim.laliga.com/public-service/api/v1/teams/rc-deportivo/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 25 |
| ELCHE CF | [`elche-c-f`](https://apim.laliga.com/public-service/api/v1/teams/elche-c-f/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 28 |
| RCD ESPANYOL | [`rcd-espanyol`](https://apim.laliga.com/public-service/api/v1/teams/rcd-espanyol/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 28 |
| GETAFE CF | [`getafe-cf`](https://apim.laliga.com/public-service/api/v1/teams/getafe-cf/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 30 |
| LEVANTE UD | [`levante-ud`](https://apim.laliga.com/public-service/api/v1/teams/levante-ud/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 27 |
| REAL MADRID CF | [`real-madrid`](https://apim.laliga.com/public-service/api/v1/teams/real-madrid/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 30 |
| MALAGA CF | [`malaga-cf`](https://apim.laliga.com/public-service/api/v1/teams/malaga-cf/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 28 |
| OSASUNA | [`c-a-osasuna`](https://apim.laliga.com/public-service/api/v1/teams/c-a-osasuna/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 27 |
| RACING DE SANTANDER | [`r-racing-club`](https://apim.laliga.com/public-service/api/v1/teams/r-racing-club/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 28 |
| RAYO VALLECANO | [`rayo-vallecano`](https://apim.laliga.com/public-service/api/v1/teams/rayo-vallecano/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 31 |
| REAL SOCIEDAD | [`real-sociedad`](https://apim.laliga.com/public-service/api/v1/teams/real-sociedad/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 29 |
| SEVILLA | [`sevilla-fc`](https://apim.laliga.com/public-service/api/v1/teams/sevilla-fc/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 31 |
| VALENCIA | [`valencia-cf`](https://apim.laliga.com/public-service/api/v1/teams/valencia-cf/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 31 |
| VILLARREAL | [`villarreal-cf`](https://apim.laliga.com/public-service/api/v1/teams/villarreal-cf/squad-manager?limit=50&offset=0&orderField=id&orderType=DESC&seasonYear=2026&contentLanguage=es&subscription-key=c13c3a8e2f6b46da9c5c425cf61fab3e) | 26 |

`limit=50` cubre de sobra la plantilla más numerosa (33 fichas), así que no hace
falta paginar con `offset`.

## Estructura de la respuesta

```json
{
  "total": 28,
  "squads": [
    {
      "id": 84308,
      "shirt_number": 1,
      "current": true,
      "loan": false,
      "loan_to": false,
      "position": { "name": "Portero", "slug": "portero" },
      "team": { "slug": "d-alaves", "shortname": "ALA", "color": "#0f39b8" },
      "person": {
        "name": "Antonio Sivera",
        "nickname": "Sivera",
        "firstname": "Antonio",
        "lastname": "Sivera",
        "date_of_birth": "1996-08-11T00:00:00+00:00",
        "height": 188,
        "country": { "id": "ES" }
      },
      "role": { "name": "Jugador", "slug": "jugador" },
      "photos": { "001": { "512x556": "https://assets.laliga.com/..." } }
    }
  ]
}
```

### Campos útiles

| Campo | Uso |
| --- | --- |
| `shirt_number` | Dorsal oficial. Puede ir desactualizado a principio de temporada. |
| `person.nickname` | Nombre corto, el que suele imprimir Panini. |
| `person.name` | Nombre completo, mejor para emparejar con el checklist. |
| `position.name` | `Portero`, `Defensa`, `Centrocampista` o `Delantero`. |
| `role.slug` | `jugador`, `entrenador` o `segundo-entrenador`. |
| `loan` / `loan_to` | Cesiones entrantes y salientes. |
| `current` | Si la ficha sigue activa en la plantilla. |
| `photos` | Retratos oficiales en PNG. |

Para quedarse sólo con futbolistas hay que filtrar `role.slug == "jugador"`; en
caso contrario se cuelan el entrenador y el segundo entrenador.

## Fotos de jugador

Las imágenes viven en `assets.laliga.com` y siguen este patrón:

```
https://assets.laliga.com/squad/2026/t<equipo>/p<persona>/<tamaño>/p<persona>_t<equipo>_2026_0_<variante>_000.png
```

| Variante | Encuadre | Tamaños |
| --- | --- | --- |
| `001` | Retrato vertical, fondo recortado | `64x70` … `2048x2225` |
| `002` | Cuadrado | `64x64` … `2048x2048` |
| `003` | Cuadrado alternativo | `64x64` … `2048x2048` |
| `004` | Cuadrado alternativo | `64x64` … `2048x2048` |

Son PNG con transparencia y encuadre uniforme, bastante mejores que los retratos
de Transfermarkt para dibujar los cromos que no tienen imagen oficial.

## Cómo actualizar

El proceso está automatizado en `generar_plantillas_laliga.py`:

```powershell
.\.venv\Scripts\python.exe generar_plantillas_laliga.py --refrescar
.\.venv\Scripts\python.exe generar_plantillas_html.py
```

1. Recupera los 20 slugs con el endpoint de equipos filtrado por competición.
2. Descarga la plantilla de cada equipo y cachea la respuesta en `.cache_laliga/`.
3. Escribe `laliga_equipos.csv` y `laliga_plantillas.csv` con todos los campos
   útiles, ordenando cada plantilla por demarcación y dorsal.
4. Regenera `supabase/laliga_plantillas.sql` con un `delete` y los `insert`
   completos dentro de una transacción, para limpiar tabla e importar de nuevo.
5. `generar_plantillas_html.py` construye `album/plantillas.html`, la vista de
   sólo lectura con las plantillas reales.

Las tablas `public.laliga_equipo` y `public.laliga_plantilla` se crean con la
migración `supabase/migrations/20260902120000_laliga_squads.sql`, que las
recrea desde cero porque todo su contenido se regenera desde la API. La clave
primaria de las fichas es `clave`, no `squad_id`, porque LALIGA publica los
fichajes recién anunciados sin identificador.

Para emparejar con el checklist Panini se usa `person.name` y `person.nickname`
normalizados contra `coleccion_panini_revisada.csv`, y sólo se actualiza dorsal,
posición o foto cuando la coincidencia es fiable.

## Limitaciones

- Los dorsales no siempre están al día, sobre todo tras el mercado de invierno.
- Los fichajes más recientes llegan sin `id`, `person.id`, `opta_id` ni dorsal
  (unas 15 fichas). Por eso la clave primaria de la tabla es `clave`, que el
  generador construye con el slug del equipo y, cuando no hay `id`, con el
  nombre normalizado del jugador.
- Muchos nombres vienen con espacios sobrantes; el generador los recorta.
- La API confirma quién **está** en la plantilla, pero no informa de traspasos;
  para las salidas se sigue usando BeSoccer.
- La clave pública puede cambiar.
- Las imágenes se enlazan desde `assets.laliga.com`; no se copian al repositorio.

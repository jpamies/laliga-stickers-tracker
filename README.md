# LALIGA Stickers Tracker

Álbum estático para seguir la colección Panini LALIGA 2026-27.

## Funciones

- 514 cromos y variantes del checklist físico.
- Buscador y filtros por equipo, sección y estado.
- Estados `No lo tengo`, `Lo tengo` y `Pegado`.
- Contador y vista de cromos repetidos.
- Progreso almacenado localmente en el navegador.
- Imágenes asociadas de forma conservadora por jugador y equipo.
- Estrategia de pegado basada en plantillas de Transfermarkt.
- Importación y exportación del progreso.

## Desarrollo

Regenerar los datos y el álbum:

```powershell
.\.venv\Scripts\python.exe generar_mapeo_imagenes.py
.\.venv\Scripts\python.exe generar_album.py
```

Ejecutar las pruebas:

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

La documentación sobre el manifiesto digital está en
[`PANINI_DIGITAL.md`](PANINI_DIGITAL.md).

## Publicación

Cada cambio subido a la rama `main` despliega automáticamente la carpeta
`album/` mediante GitHub Pages.

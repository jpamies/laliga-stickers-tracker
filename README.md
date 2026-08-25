# LALIGA Stickers Tracker

Álbum estático para seguir la colección Panini LALIGA 2026-27.

## Funciones

- 514 cromos y variantes del checklist físico.
- Buscador y filtros por equipo, sección y estado.
- Estados `No lo tengo` y `Lo tengo`, también con clic directo en la imagen.
- Confirmación antes de retirar un cromo de la colección.
- Decisión personal `No pegar`, inicializada desde la recomendación de Transfermarkt.
- Contador y vista de cromos repetidos.
- Progreso local sin conexión y sincronización opcional por cuenta.
- Imágenes asociadas de forma conservadora por jugador y equipo.
- Estrategia de pegado basada en plantillas de Transfermarkt.
- Importación y exportación del progreso.
- Enlaces públicos revocables del álbum en modo sólo lectura.
- Amigos mediante invitación, comparación de repetidos y propuestas de intercambio.

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
5. Autoriza la URL local y la de GitHub Pages en la aplicación de Clerk.

Las funciones sociales se gestionan con migraciones versionadas:

```powershell
supabase link --project-ref cjwssgaigkagoocwiecq
supabase db push
```

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

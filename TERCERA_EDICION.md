# Tercera edición del checklist

Panini publicó el [checklist oficial de la tercera
edición](https://www.panini.es//media/paniniFiles/Checklist_LALIGA_2026-27-3_ED.pdf)
el 25 de septiembre de 2026. Cuatro días antes habíamos registrado esos mismos
cromos a partir del listado que circulaba por la web, y sin numerar los BIS
porque el anuncio no los numeraba.

Este documento recoge en qué acertó ese registro previo, qué corrige el PDF y
qué erratas trae el propio checklist. `coleccion_panini.csv` ya sale del PDF
oficial, así que el importador provisional (`importar_tercera_edicion.py`) se ha
retirado.

## Resumen

| | |
| --- | ---: |
| Cromos en el checklist oficial | 589 |
| Cromos que ya teníamos registrados | 589 |
| Cromos cuya identidad coincide | 589 |
| Diferencias de dato | 7 |
| Erratas del PDF corregidas a mano | 2 |

Las 589 entradas coinciden una a una. Lo que aporta el PDF es la **numeración
de los BIS**, que es justo lo que no se podía deducir.

## Los BIS ya tienen casilla

Los 24 cromos BIS se registraron sin número porque el anuncio no lo daba. Se
barajó deducirlo con la regla «un BIS sustituye a quien se ha ido», pero no
cuadraba: el Espanyol tenía tres BIS y sólo dos huecos vacantes, y el Deportivo
y el Málaga tenían BIS sin ningún hueco libre.

El PDF confirma que **la regla acierta en 17 de 24**, así que colocarlos a ojo
habría fallado en siete.

| Equipo | Casilla | Jugador | Ocupante anterior | ¿Se había ido? |
| --- | ---: | --- | --- | :---: |
| Deportivo Alavés | 8BIS | Garcés | Parada | sí |
| Deportivo Alavés | 20BIS | Mariano | Boyé | no |
| Atlético de Madrid | 10BIS | Grimaldo | Ruggeri | sí |
| Atlético de Madrid | 16BIS | Arnau Ortiz | Almada | sí |
| FC Barcelona | 18BIS | Abdelkarim | Ferran Torres | sí |
| Real Betis | 11BIS | Deossa | Amrabat | sí |
| RC Celta de Vigo | 19BIS | Hugo González | Jutglà | no |
| Deportivo | 8BIS | Bright Ede | Dani Barcia | no |
| Deportivo | 14BIS | Gijselhart | José Ángel | no |
| RCD Espanyol | 6BIS | Drkusic | Rubén Sánchez | sí |
| RCD Espanyol | 9BIS | Hinojo | Miguel Rubio | sí |
| RCD Espanyol | 15BIS | Javi Hernández | Marcos Fernández | no |
| Getafe CF | 19BIS | Ünal | Luis Vázquez | sí |
| Levante UD | 6BIS | Nacho Pérez | Elgezabal | sí |
| Levante UD | 16BIS | Thiago Fernández | Tunde | sí |
| Real Madrid CF | 7BIS | Konaté | Asencio | no |
| Málaga CF | 6BIS | Recio | Murillo | no |
| Osasuna | 16BIS | Dubasin | Iker Benito | sí |
| Racing de Santander | 8BIS | Pedro Felipe | Javi Castro | sí |
| Racing de Santander | 13BIS | Sergio Martínez | Íñigo | no |
| Racing de Santander | 15BIS | Zabiri | Suleiman | sí |
| Rayo Vallecano | 7BIS | Vertrouwd | Nobel Mendy | sí |
| Rayo Vallecano | 10BIS | Pelayo | Pep Chavarría | sí |
| Sevilla | 8BIS | Julio Díaz | Nianzou | sí |
| Sevilla | 19BIS | Miguel Sierra | Akor Adams | sí |

El 18BIS de Abdelkarim ya lo traía numerado el anuncio, y coincide.

El checklist no marca el 20BIS del Alavés con la etiqueta de tercera edición,
aunque venía en su anuncio. Se respeta lo que dice el PDF, así que ese cromo
consta como de la primera; por eso la tercera edición suma 51 cromos y no 52.

Colocarlos cambia bastante el informe de optimización: los huecos sin ningún
jugador activo bajan de 29 a 13, porque muchos BIS son precisamente el relevo
de quien se fue.

## Nteka cambia de equipo

El hueco 11 de dos equipos se reorganiza porque Nteka pasó del Racing al Rayo:

| | Segunda edición | Tercera edición |
| --- | --- | --- |
| Racing de Santander | 11A Maguette, 11B Nteka | 11 Maguette |
| Rayo Vallecano | 11 Pedro Díaz | 11A Pedro Díaz, 11B Nteka |

Es el único cromo que desaparece del álbum: el `11B` del Racing ya no existe.
El del Rayo es un cromo nuevo, con otra camiseta.

Esta renumeración obligó a fijar a mano los identificadores de Maguette y Pedro
Díaz. El progreso se guarda por identificador, y al correrse los números el de
Pedro Díaz habría acabado apuntando a Vertrouwd.

## Diferencias de dato

Siete cromos tenían algún campo distinto. En cuatro casos el PDF sólo abrevia
(«Javi Galán» → «Galán», «Real Madrid» → «R. Madrid»), y en tres hay una
discrepancia real, arbitrada con la plantilla oficial de LALIGA:

| Cromo | Nuestro registro | Checklist | LALIGA | Quién acertaba |
| --- | --- | --- | --- | --- |
| Alavés 10 (Mikel Rodríguez) | defensa | medio | Defensa | nuestro |
| UF26 (Javi Morcillo) | delantero | medio | Centrocampista | checklist |
| UF27 (Núñez) | delantero | defensa | Defensa | checklist |

La identidad de los 589 cromos coincide en todos los casos, incluido el 10 del
Alavés: el checklist sólo pone «Rodríguez» y el club tiene tres, pero la
posición dentro de la página permitió acertar con Mikel.

## Erratas del checklist

Dos errores del PDF se corrigen al extraerlo, con la plantilla de LALIGA como
árbitro. Están en `CHECKLIST_FIXES`, dentro de `extraer_checklist.py`.

| Cromo | Dice el checklist | Debería decir | Comprobación |
| --- | --- | --- | --- |
| Deportivo 14BIS | Gijselhat | Gijselhart | LALIGA lo inscribió como Teun Gijselhart |
| UF26 | Javi Morcillo (Sevilla FC) | Javi Morcillo (Elche CF) | Juega en el Elche con el dorsal 47 |

El checklist también escribe «Nuñez» donde LALIGA usa «Núñez», pero eso no
afecta al emparejamiento, que ignora las tildes.

## Cromos que no se pegan

Dos cromos de la tercera edición son de jugadores que ya no están en el club.
Se imprimieron a tiempo y saldrán en los sobres, así que siguen en el checklist,
pero el álbum los marca para no pegarlos:

- **Sergio Martínez** (Racing, 13BIS): fichó por el Real Madrid Castilla y no
  tiene ficha del primer equipo.
- **Gijselhart** (Deportivo, 14BIS): desapareció de la plantilla oficial entre
  el 17 y el 21 de septiembre.

## Nombres que no encuentran su ficha

Panini imprime el nombre por el que se conoce al jugador y LALIGA lo inscribe
con el del registro civil, así que algunos cromos no casan por parecido de
texto. Cuando se ha comprobado a mano a quién corresponde, el emparejamiento se
fija con un alias en `LALIGA_ALIASES`:

| Cromo | Lo inscribe LALIGA como | |
| --- | --- | --- |
| Ximo Navarro (Deportivo 9A) | Joaquín Navarro Jiménez, dorsal 23 | «Ximo» es su apodo |
| Williams (Athletic 19) | Iñaki Williams, dorsal 9 | Nico tiene el cromo 18 |

El segundo caso obligó además a cambiar el orden en que se busca. Un nombre que
encaja con dos jugadores se daba por ambiguo de inmediato, antes de mirar los
alias, que son justo lo que dice a cuál de los dos se refiere.

Quedan cuatro cromos por confirmar. En todos ellos el jugador ha desaparecido
de la plantilla oficial, pero el nombre es demasiado corto o demasiado común
para darlo por perdido sin verlo:

| Cromo | Se parece a |
| --- | --- |
| Giménez (Atlético 8B) | Diego Simeone |
| Fer López (Celta 15) | Rober Fernández |
| Juanpe (Málaga 13B) | Juan Francisco Fernández Martín |
| Oso (Sevilla 11) | Ibrahima Sow |

## Cómo se lee el PDF

La tercera edición cambia dos detalles de formato respecto a la segunda, y
ambos rompían el extractor:

- Separa el prefijo y la variante con un espacio: `UF 21` y `8 BIS`, donde antes
  ponía `UF21` y `8BIS`. El CSV guarda siempre la forma sin espacio.
- Marca cada cromo con la edición en que apareció, ahora con tres valores
  posibles: sin marca (primera), `2ªed` y `3ª ed`.

También abrevia algunos clubes en Últimos Fichajes (`R. Madrid`, `Racing`), que
se traducen a su nombre canónico.

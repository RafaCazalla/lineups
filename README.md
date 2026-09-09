# BeSoccer · Campo 3D

Visor 3D interactivo de alineaciones, como paso previo a una app para Apple Vision Pro.
**Toda la geometría se genera por código**: no hay ni un `.glb`, ni un `.fbx`, ni ninguna
textura descargada. El campo es reglamento FIFA dibujado sobre un canvas.

Los datos son **reales, de la API de BeSoccer**: Real Madrid 2 – 1 Inter (partido
`208696`, temporada 2027), con las alineaciones, las notas, los goles, las tarjetas, los
cambios y las estadísticas del partido tal como los devuelve la API.

## Abrirlo

```bash
open index.html                  # doble clic vale: no hay build ni npm
python3 -m http.server 8000      # para probarlo en un móvil de verdad
```

Necesita red: three.js viene de jsDelivr con la versión fijada (`three@0.186.0`), y los
escudos y los retratos de `cdn.resfu.com`.

### Enlaces directos

| Parámetro | Qué hace |
|---|---|
| `?vista=` | `completo` · `local` · `visita` · `tactica` · `ras` |
| `?jugador=` | `l10` (local, dorsal 10) · `v9` (visitante, dorsal 9) |
| `?equipo=` | `todos` · `local` · `visitante` |
| `?etiquetas=0` `?dorsales=0` `?pases=1` `?media=1` `?stats=1` | estado inicial de los paneles |
| `?debug` | fps, llamadas de dibujo y triángulos (también con la tecla **D**) |

Ejemplo: `index.html?vista=tactica&pases=1&etiquetas=0` deja la forma de los dos equipos.

### Cómo se usa

Arrastrar orbita · rueda o pinza acerca · botón derecho o dos dedos desplaza ·
clic o toque en un jugador abre su ficha · **← →** cambia de jugador · **Esc** cierra.

## Desplegado

- GitHub Pages: <https://rafacazalla.github.io/lineups/>

**Pendiente en Vercel.** En este Mac no hay Node, así que no hay CLI de Vercel, y no había
token ni `.vercel` en ningún repo. Para montarlo: importar `RafaCazalla/lineups` en
<https://vercel.com/be-soccer-product> como proyecto estático sin build. El `vercel.json`
ya está en el repo con los encabezados (`noindex`, sin caché, sin `X-Frame-Options`, para
que el hub pueda previsualizarlo en su iframe). En Pages esos encabezados **no** se
aplican; el `noindex` lo lleva el propio HTML en una `<meta>`.

## Los datos

```bash
export BESOCCER_KEY=...                       # la clave NO vive en el repositorio
python3 tools/besoccer_datos.py 208696 --year 2027 \
        -o data/partido-208696.json --inline index.html
```

`--inline` sustituye el bloque `const PARTIDO = …` de `index.html` entre los marcadores
`/* PARTIDO:inicio */` … `/* PARTIDO:fin */`, escapando `<` como `<`: sin eso, un
nombre que contuviera `</script` tumbaría la página. **No pegues el JSON a mano.**

Tres peticiones: `match_lineups`, `match_events_stats` y **`playerStats`, una por
jugador** (22 más). `--sin-stats` las salta si solo hace falta la alineación.

Y tres reglas:

- **La clave de la API no se incrusta nunca.** Se lee de `BESOCCER_KEY` o de `--key`, y
  solo se incrusta el resultado. Este prototipo se despliega en un sitio público, y una
  clave en el HTML es una clave regalada. Si algún día tiene que pedir en caliente, la
  clave va en una función de Vercel con la clave en variable de entorno, nunca en el
  cliente.
- **Los datos van incrustados, no se piden al abrir.** Así funciona con doble clic, sin
  servidor y sin CORS, que es lo que hace que se pueda enseñar en cualquier sitio.
- **Lo que la API no da, no está.** Ver abajo.

### Lo que la API da, y lo que no

| Da | Cómo se usa |
|---|---|
| 22 titulares con dorsal, nombre, rol, nota, color de la nota, foto, edad, capitán | etiquetas, dorsales y ficha |
| goles, tarjetas con minuto y minuto de sustitución, por jugador | marcas en la etiqueta y en la ficha |
| goles, tarjetas, cambios y ocasiones del partido, con minuto y jugador | línea de tiempo de la cabecera |
| marcador, minuto (90+3) y estado | cabecera; el reloj **solo** corre si está en directo |
| entrenadores, tácticas, nota y edad media de cada equipo | segunda línea de la cabecera |
| 13 estadísticas de partido (posesión, tiros, pases, faltas…) | panel «Estadísticas del partido» |
| escudos y retratos por id | imágenes reales, no marcadores de posición |

**No da coordenadas de los jugadores.** Manda el nombre de la táctica (`4-2-3-1`,
`3-5-2`), un `pos` de 1 a 11 que recorre las líneas de atrás hacia delante, y
`mirror_*_tactic`. `posiciones()` reparte con eso: la profundidad por línea y el ancho a
partes iguales dentro de cada línea. **Es la forma del equipo, no dónde estuvo cada
uno** — y la propia API lo avisa: *«Alineación generada automáticamente según las
posiciones de los jugadores. Puede no coincidir con la utilizada.»* Ese aviso está en el
tooltip de la línea de tácticas. Si BeSoccer tiene la tabla real de casillas por táctica,
entra en esa única función.

**El endpoint de estadísticas por jugador es `playerStats`, no `match_player_stats`.**
El segundo devuelve `{"teams":[]}` con cualquier `vr`; el primero, 10 KB por jugador. De
ahí sale casi toda la ficha:

| Da | Cómo se usa |
|---|---|
| secciones (Acciones clave, Ofensivo, Distribución, Defensa) con **su propia nota** | secciones plegables de la ficha, con su nota en la cabecera |
| filas con título, valor y **color**: verde suma en la nota, rojo resta | las filas, con el color tal cual: aquí no se decide qué es bueno |
| `isMvp`, y el desglose de la nota en bonificaciones y penalizaciones | sello MVP y las dos chapas «Suma +8.9 / Resta −0.5» |
| `fieldStats.heatmap`: los toques del jugador, normalizados | **el mapa de calor, pintado sobre el campo 3D** |
| `fieldStats.shots`: cada tiro con minuto, pie, coordenada y **xG** | filas bajo la sección ofensiva |
| `role` fino (`ED`, `CAI`, `MCD`…) | «Extremo derecho» en vez de «Delantero» |

**El mapa de calor va sobre el campo, no en una miniatura.** Al elegir un jugador se
pinta su mancha sobre el césped a escala real, y se apaga al soltarlo. Es una capa con su
propia textura de 1024 px, una llamada de dibujo, y es justo lo que justifica el 3D:
poder mirar la mancha desde el ángulo que quieras en vez de en un recuadro de 250 px. La
rampa va de transparente a cian, amarillo, naranja y rojo — sobre césped una rampa verde
no se ve, que es el error evidente — y el alfa y la luminosidad crecen con la intensidad,
así que se lee también sin distinguir el color.

La ficha **no calcula nada**: pinta la estructura que manda la API. El verde y el rojo de
cada cifra los pone BeSoccer, no este prototipo. La única licencia es plegar todas las
secciones menos la primera: con las cuatro abiertas la ficha pasa de cuarenta filas y
deja de leerse.

### Alineación vs posición media real

El mapa de calor da algo que la alineación no: **dónde jugó cada uno de verdad**. El
interruptor «Posición media real» mueve las 22 fichas al centroide de sus toques, con
transición animada, porque el movimiento entre las dos es la información.

- **Alineación** (por defecto) es la casilla deducida del nombre de la táctica. Es la
  forma del equipo, y la API avisa de que es automática.
- **Posición media** es dato medido. En un partido completo de ida y vuelta tira hacia el
  centro del campo y **los dos equipos se solapan**: eso no es un fallo del prototipo, es
  el partido.

Por eso hay **selector de equipo** (Todos · un equipo · el otro) arriba del panel
izquierdo: con los 22 en posición media real no se lee nada, y de once en once sí. Va
ahí y no en las pastillas de la esquina porque esas mueven la cámara y esto cambia lo que
hay en el campo; mezclarlas haría que «Once local» significase dos cosas.

Al esconder un equipo, sus fichas se mandan mil metros abajo en vez de escalarlas a cero:
una matriz de instancia con escala 0 es singular, el raycaster la invierte y devolvería
`NaN` en lugar de «aquí no hay nada». El raycaster además comprueba el corte, las flechas
← → se saltan a quien no está, y si el jugador abierto se queda fuera se suelta la ficha.

El eje `x` de la API va de la portería propia a la contraria **para cada jugador**, así
que el visitante se espeja en los dos ejes. El espejo en `x` está comprobado con los dos
porteros (0,08 y 0,11 desde su propia portería). El de `y`, con un cruce de datos: el
extremo derecho local (Brahim, 0,28) y el carrilero izquierdo visitante (Carlos Augusto,
0,21) caen en la misma banda, que es el duelo que tiene que haber. Sin ese cruce, un
carrilero acaba en la banda equivocada y nadie lo nota.

**Las «líneas de pase» no son pases.** Es un grafo de proximidad: cada jugador con sus
tres compañeros más cercanos, hasta 26 m. Dibuja la forma del equipo. Con datos reales de
pases se sustituye `lineasDePase()` y nada más.

**Los colores de equipación se ponen a mano** en `EQUIPACIONES`, por id de equipo, porque
la API no los da. Lo que no esté en la tabla sale en gris neutro, no en un color falso.
Los colores de las líneas de pase y de las barras salen de la paleta validada, no de la
camiseta: tienen que distinguirse sobre césped y bajo daltonismo.

## La marca del campo

El logo de BeSoccer va **pintado sobre el césped**, como en un campo de verdad: dos
marcas en esquinas opuestas —inferior izquierda y superior derecha—, la segunda girada
180° para que se lea desde la banda contraria. Se dibujan con las proporciones del logo
(cuadrado redondeado, línea de medio campo vertical partida por el círculo, anillo y
punto) medidas sobre el original, en `marcaCesped()`, dentro de la textura del césped y
**antes** de las líneas reglamentarias: una línea siempre gana a la pintura de marca.

El cuadrado, que en el logo es verde, aquí se queda en una mancha casi invisible: sobre
césped un verde sobre verde no aporta nada, y lo que hace reconocible la marca es el
anillo con la línea. Si hay que meter el logo oficial en SVG o PNG, es un `drawImage`
dentro de esa función, con la misma escala en metros.

Como la marca lleva texto, **la textura del césped se rehace cuando carga la
tipografía**, igual que el atlas de dorsales: si se dibuja antes, «BeSoccer» sale en la
fuente de reserva.

## Lo que hay dentro

Un solo `index.html`, en bloques numerados:

| Bloque | Qué contiene |
|---|---|
| 1 · Medidas | `M`: reglamento FIFA en metros. **1 unidad de three = 1 metro.** |
| 1 bis · El partido | `PARTIDO`, incrustado por la herramienta |
| 2 · Renderizador | WebGL2, ACESFilmic, `RoomEnvironment`, una luz direccional |
| 3 · El campo | textura de césped, líneas, marca de BeSoccer, zócalo, sombra de contacto, porterías, banderines |
| 3 bis · Los jugadores | fichas, dorsales en billboard, etiquetas HTML, líneas de pase, capa de calor |
| 4 · Cámara | `OrbitControls` con límites, encuadre calculado, puntos de vista con transición |
| 5 · Interfaz | cabecera, interruptores, selección, ficha, estadísticas del partido |
| 6 · Bucle | render, redimensionado y contador de rendimiento |

Cambiar una medida en `M` cambia el campo entero: las líneas se dibujan de ahí.

## Decisiones que conviene no deshacer

### El campo

- **Las líneas son textura, no geometría.** Se dibujan sobre un canvas 2D de 4096 px
  (~35 px/m, así una línea de 12 cm cae en 4 px) y se usan como mapa del césped.
- **El césped no lleva ruido por píxel.** Lleva manchas grandes. El ruido fino en una
  textura de 4096 px hace moiré en cuanto el campo se ve de lejos.
- **El zócalo tiene la tapa 5 cm por debajo del césped.** Dos caras a la misma cota,
  vistas a 130 m, se pelean por la profundidad y el zócalo aparece atravesando el campo
  en diagonal. Por lo mismo el plano cercano de la cámara está a 2 m y no a 0,5.
- **La sombra de contacto es una textura, no una luz.** Es lo que hace que el campo
  parezca apoyado en algo en vez de flotando. Cuesta una llamada de dibujo.
- **Sin estadio, y a propósito.** La grada es un modelo de Blender, y es donde se van el
  tiempo y los megas. En unas gafas el estadio es la habitación del usuario.

### La cámara

- **La distancia no se escribe a mano, se calcula.** `distanciaEncuadre()` proyecta las
  ocho esquinas de la losa y busca la distancia a la que caben todas. En vertical el
  encuadre gira 90° para que los 105 m caigan sobre el lado largo.
- **La inercia no es un adorno.** `dampingFactor 0.05` es la mitad de la sensación de
  calidad; sin ella parece un visor técnico.
- **El objetivo no se va.** Se orbita alrededor del campo, no se navega por la escena. El
  pan lleva correa: el objetivo no puede salir del campo.
- **`A ras de césped` suelta el límite polar** a 1,555 rad. Con el tope normal de 1,45,
  mirando casi horizontal, `OrbitControls` devolvía la cámara hacia arriba.

### Los jugadores

- **Sombra, disco y poste van en `InstancedMesh`:** una llamada de dibujo cada una para
  los 22, no veintidós.
- **El dorsal es un atlas de texturas y 22 cuadros en una sola malla.** Las UV apuntan a
  su celda; lo que se reescribe cada cuadro son las posiciones, orientadas con los ejes
  de la cámara. Eso es el billboard, y cuesta una llamada.
- **Los cuadros se ordenan de lejos a cerca cada cuadro.** Sin ordenar, dos dorsales que
  se solapan se mezclan en el orden equivocado y el de detrás tapa al de delante.
- **El atlas se dibuja después de `document.fonts.load`,** con tope de 2,5 s. Antes, los
  números salían en la tipografía de reserva; con el tope, si Google Fonts no contesta el
  prototipo arranca igual.
- **El nombre va en HTML (`CSS2DRenderer`), nunca en textura.** La etiqueta lleva los
  colores de la equipación, y las marcas de gol y tarjeta que da la API: la alineación ya
  cuenta el partido sin abrir ninguna ficha.
- **El clic va contra el disco Y contra el dorsal.** El blanco principal es el disco, como
  pide el encargo, pero la etiqueta lo tapa: si solo respondiera el disco, tocar el nombre
  no haría nada. Las etiquetas HTML no son blanco de nada (`pointer-events:none`).
- **Un arrastre orbita, solo un toque limpio selecciona.** Umbral de 6 px entre el
  `pointerdown` y el `pointerup`.
- **La nota lleva el color que manda la API** (`ratingColor.lightColor`), no uno propio:
  así el mismo jugador se ve igual aquí y en la app.
- **El reloj solo corre si el partido está en directo.** Un cronómetro andando bajo un
  resultado final miente sobre lo que se está viendo.
- **La capa de calor se apaga con la selección.** Si la mancha se queda pintada al
  soltar al jugador, deja de decir de quién es.
- **Una barra sin total se queda vacía.** «Tarjetas rojas 0 – 0» no dibuja dos mitades:
  un reparto al 50 % de una nada no significa nada.

## Criterios de aceptación

| | |
|---|---|
| Bundle propio < 300 KB | ✅ 236 KB, de los que 168 KB son los datos del partido (+ three desde CDN, tipografía y escudos) |
| Orbitar 360° arrastrando | ✅ |
| Cenital ↔ ras de césped con transición | ✅ 700 ms, `easeInOutCubic` |
| Clic en jugador: se eleva, anillo y ficha | ✅ probado con eventos sintéticos |
| Etiquetas legibles a cualquier ángulo, nunca del revés | ✅ HTML, ordenadas por profundidad |
| `InstancedMesh` para los 22 discos y los 22 postes | ✅ |
| 60 fps y menos de 60 llamadas de dibujo | ✅ **19 llamadas**, 7,6k triángulos |
| Sin ningún binario de modelo en el repo | ✅ |
| Funciona con el dedo | 🟡 puesto y con eventos de puntero; **sin probar en un móvil real** |

## Lo que falta

- **El mapa de tiros sobre el campo 3D.** Los datos ya están incrustados (51 tiros con
  coordenada de origen y xG); en la ficha salen como lista, pero no dibujados. El mapa de
  calor ya está sobre el césped, así que la capa y la rampa se reutilizan.
- **El logo oficial en vectorial.** La marca del césped está dibujada a mano con las
  proporciones del logo; con el SVG o el PNG de marca queda idéntica.
- **Competición y jornada**: no vienen en estas dos peticiones. La cabecera lleva
  entrenadores y tácticas en su lugar, y no se inventa una jornada.
- **Suplentes.** La API los da (`bench`), con el minuto en que entraron. Cabe un banquillo
  al borde del campo, que es lo que hacía el interruptor «Mostrar banquillo» de la maqueta.
- **Forma ofensiva, defensiva y balón parado**, los tres puntos de vista del documento de
  encargo. No son ángulos de cámara: son tres juegos alternativos de posiciones, y no hay
  datos tácticos para sostenerlos.

## El puente a las gafas

Safari en visionOS ejecuta WebXR, y three.js lo soporta. Con `renderer.xr.enabled`, el
`VRButton` y el campo escalado a tamaño de mesa (factor ~0,02), este mismo fichero
servido por HTTPS se abre en el Vision Pro sin escribir una línea de Swift. Habrá que
sustituir `OrbitControls` por manipulación directa —agarrar el campo y girarlo con las
manos— y medir el coste del estéreo, que dobla el trabajo del render. Las etiquetas HTML
de `CSS2DRenderer` **no** sobreviven al modo inmersivo: ahí los nombres tendrían que
pasar a textura o a un plano de three.

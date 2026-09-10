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
| `?estadio=1` | arranca dentro de Ewood Park en vez del campo suelto |
| `?etiquetas=0` `?dorsales=0` `?pases=1` `?media=1` `?stats=1` | estado inicial de los paneles |
| Combinación que mejor se lee | `?equipo=visitante&media=1&pases=1&vista=tactica` |
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
        --pases data/passmatrix-208696.xml \
        -o data/partido-208696.json --inline index.html
```

`--inline` sustituye el bloque `const PARTIDO = …` de `index.html` entre los marcadores
`/* PARTIDO:inicio */` … `/* PARTIDO:fin */`, escapando `<` como `<`: sin eso, un
nombre que contuviera `</script` tumbaría la página. **No pegues el JSON a mano.**

Tres peticiones: `match_lineups`, `match_events_stats` y **`playerStats`, una por
jugador** (22 más). `--sin-stats` las salta si solo hace falta la alineación. Y `--pases`,
que no es una petición: lee un `passMatrix` de Opta de un fichero.

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

### El mapa de pases

Sale de un **`passMatrix` de Opta** (`data/passmatrix-208696.xml`), que es una fuente
distinta de la API de BeSoccer. Se unen por **(equipo, dorsal)**, lo único que tienen en
común: los identificadores de jugador de las dos no se parecen en nada. Casan los 22
titulares, y las posiciones medias de Opta coinciden con los centroides de los mapas de
calor de BeSoccer (Cucurella 44,8/83,5 frente a 43,5/81,9), así que las dos fuentes se
validan entre ellas.

- **744 pases entre titulares.** Los pases con suplentes se descartan: los suplentes no
  están en el campo del prototipo.
- **Se dibujan todas las parejas que se pasaron el balón, aunque fuera una vez.** Se probó
  con umbral y fue un error: un portero que reparte poco se quedaba con dos líneas y la red
  parecía **rota**, que es justo lo que no puede pasar en un mapa de pases. Courtois tiene
  siete conexiones, y seis de ellas son de uno a cinco pases.
- **El peso lo lleva el dibujo, no el filtro.** Ancho y opacidad se escalan contra la
  pareja más fuerte **de su equipo** —el Inter dio 452 pases entre titulares y el Madrid
  292, y con un máximo global el que más pasa sale más gordo por serlo— y con curva
  agresiva (`rel^1.15`): con 48 parejas por equipo, si las flojas no se hunden no hay
  estructura que ver. Una pareja de un pase es un hilo casi transparente; la más fuerte,
  una cinta ancha.
- **Las cintas no llegan al jugador: se paran a 2,4 m.** Si mueren en el centro del nodo,
  los jugadores desaparecen bajo el nudo y la red deja de leerse. Es el cambio que más se
  nota de todos.
- **El sentido no se dibuja.** Una cinta que se estrecha se lee mal y se presta a leerla
  al revés. La dirección va en la ficha, en «Pases a compañeros», con su número.
- **Con un jugador elegido, sus cintas mandan y el resto se apagan.** Si no, la red pesa
  lo mismo entera y no se ve de quién es cada pase. Y sus parejas dejan de ser una cinta
  sin sentido: pasan a **dos carriles, ida y vuelta**, con un pulso que los recorre en la
  dirección del pase. La matriz es dirigida, así que eso no es adorno: es el dato que la
  cinta única no puede enseñar.
- **El pulso va en blanco y aditivo, no en el color del equipo.** El negro del Inter,
  sumado, no ilumina nada. Son dos mallas sobre la misma geometría: la base lleva el
  color y el pulso la luz.
- **Con `prefers-reduced-motion` queda el carril y se va el pulso.** La información está
  en el ancho y en el sentido, no en la animación.
- Es una malla de dos triángulos por pareja con color por vértice: **una llamada de
  dibujo**, y el ancho puede variar. `LineSegments` no sirve: el grosor de línea lo
  ignoran casi todas las plataformas.
- Va con `side: DoubleSide` a propósito: el bobinado de estos cuadros deja la normal
  hacia abajo, y con `FrontSide` el mapa entero desaparece al mirar el campo desde
  arriba, que es de donde se mira siempre.

Con los dos equipos y todos a la vez es una maraña; con el selector de equipo puesto en
uno, es una red de pases legible. Esa es la combinación que enseña algo.

**Los colores de equipación se ponen a mano** en `EQUIPACIONES`, por id de equipo, porque
la API no los da. Lo que no esté en la tabla sale en gris neutro, no en un color falso.
Los colores de las líneas de pase y de las barras salen de la paleta validada, no de la
camiseta: tienen que distinguirse sobre césped y bajo daltonismo.

## El escenario: campo suelto o estadio

El engranaje de la barra inferior abre un menú con tres opciones:

- **Por defecto** — el campo suelto generado por código. Pesa 0 y siempre está.
- **Ewood Park** (Blackburn Rovers) — GLB de 577 KB.
- **Ibn Batouta** (Tánger) — GLB de 3,5 MB.

Los dos estadios **solo se descargan al elegirlos**. Meterlos en el arranque sería
pagarlos siempre por una opción que casi nadie va a tocar.

Cada escenario lleva su **paleta por nombre de material**, su caja de encuadre y las
medidas de su cuenco (para el muro que oculta etiquetas). Lo que no esté en la paleta se
queda con el color que trae el GLB.

Los modelos se guardan **uno por id** y se van escondiendo, no descargando: volver a uno
ya visto es instantáneo. Con una sola variable, al elegir el segundo estadio se
encontraba con que «ya había uno cargado», se saltaba la descarga y seguía enseñando el
primero.

**Alfombra de césped.** Dentro de un estadio, alrededor del campo asoma el suelo del
modelo —pista de atletismo y hormigón, en blanco—, y canta detrás de las porterías. Se
tapa con una alfombra del mismo césped pero sin marcas, del tamaño del hueco de cada
estadio, que muere bajo la primera fila como haría la hierba de verdad. Va 5 mm por
debajo del campo para que las líneas sigan siendo las nuestras.

**No es Upton Park.** El modelo de la carpeta trae un grupo llamado `jack_walker_stan`:
la Jack Walker Stand es de **Ewood Park (Blackburn Rovers)**. El nombre del menú dice lo
que el modelo es.

Dentro del estadio se apagan el zócalo y la sombra de contacto: ahí el campo no flota, se
apoya. Y **el encuadre cambia de caja** — con el estadio puesto hay que encuadrar el
estadio, no solo el césped —, así que `esquinasEncuadre` pasa a las ocho esquinas del
modelo y los puntos de vista se recalculan solos.

### Los colores no vienen en los ficheros

Merece la pena decirlo porque parece que sí: **ninguno de los nueve formatos trae los
colores del estadio.** El `.mtl` y el `.wrl` llevan los diez colores de alambre del visor
de 3ds Max —rojo, magenta, turquesa—, que se asignan por objeto y cruzan el estadio
entero, así que no separan ni una pieza; el `.dae` pone todo en un beige plano; y no hay
ni una textura.

Así que la pieza se deduce de la **geometría**, en `pieza_de()`: altura de la cara,
cuánto está tumbada, y —la que de verdad decide— **si mira hacia el campo o hacia
fuera**. Un graderío escalonado alterna huella tumbada y contrahuella vertical; tratar la
contrahuella como muro dejaba la grada a rayas azules y blancas. Las dos miran al campo,
y eso es lo que las une.

Salen cuatro piezas —`suelo`, `grada`, `cubierta`, `estructura`— como cuatro primitivas
sobre el mismo buffer de posiciones, así que el color va por material y no hay que partir
vértices en las fronteras. **La paleta vive en `index.html`, no en el GLB**: se retoca sin
volver a convertir nada. Ahora mismo, azul del Blackburn en la grada, chapa gris en la
cubierta y hormigón claro en la estructura.

El umbral de altura (`--alto-grada`, 22 m por defecto) es lo único que hay que tocar si se
cambia de estadio: por debajo, las gradas altas se pintan de estructura.

### De 32 MB de 3ds Max a 577 KB

La carpeta traía el mismo modelo en nueve formatos (`fbx`, `dae`, `obj`, `stl`, `max`,
`skp`…). En el repositorio **no va ninguno**: está en `.gitignore`. Lo que se sube es el
GLB que sale de `tools/obj_a_glb.py`, que no tiene dependencias:

```bash
python3 tools/obj_a_glb.py "campo 3d/3d-model.obj" -o assets/estadio.glb
```

- **Se tira el `.mtl`.** Son diez colores de alambre de 3ds Max —rojo, magenta, cian—
  que no significan nada. El estadio se pinta con un material propio.
- **No se guardan normales.** El material va con `flatShading`, que las calcula en el
  fragmento, así que sobran: eso quita un tercio del fichero.
- **Índices de 16 bits**, que caben porque el modelo tiene 24.685 vértices.
- Se hornea la conversión de unidades (milímetros a metros), el suelo a `y = 0` y un giro
  de 90° para que el lado largo caiga sobre el eje x, como nuestro campo. El suelo no
  estaba en cero: se detecta como la altura con más vértices, que en un estadio es el
  terreno.

Resultado: 24.685 vértices y 48.916 triángulos en 577 KB, y el césped nuestro encaja
dentro de las gradas sin tocar ni la escala.

### El estadio estaba y no se veía

Vale la pena dejarlo escrito porque costó una hora: el modelo cargaba bien, se dibujaba
—se veía en el contador de llamadas y de triángulos— y la pantalla salía vacía. **Era
gris claro sobre un fondo gris claro.** Con el estadio puesto, el fondo de la página baja
de tono (`body.con-estadio`) y el hormigón es más oscuro. Antes de buscar un fallo de
cámara, comprobar el contraste.

## El césped

Lo que hace que un campo segado se vea segado **no es el color**: es que las franjas
peinadas hacia la luz brillan y las peinadas al revés no. Por eso los dos verdes son casi
el mismo y el trabajo lo hace un **mapa de rugosidad** (`roughnessMap`, que lee el canal
verde) con las franjas alternas. Es la diferencia entre un césped a rayas y un césped.

Encima van tres cosas que delatan a un césped dibujado si faltan:

- **Degradado dentro de cada franja**: la hierba no refleja igual de un borde al otro.
- **Manchas grandes de tono**, nunca ruido por píxel: el ruido fino en una textura de
  4096 px hace moiré en cuanto el campo se ve de lejos.
- **Desgaste**: bocas de gol, puntos de penalti y círculo central, algo más claros y
  terrosos. Un campo jugado no está impecable.

## Leer un .blend sin Blender

El modelo de Tánger venía en dos RAR: uno con un `.blend` de 54 MB y otro con texturas.
En este Mac no hay Blender ni forma de instalarlo, así que **`tools/blend.py` lee el
fichero directamente**. Se puede porque un `.blend` es autodescriptivo: lleva dentro, en
el bloque `DNA1`, la definición de todas sus estructuras, y con eso se resuelven los
punteros y se sacan objetos, mallas, polígonos y materiales. Probado con Blender 2.79.

Una trampa que cuesta encontrar: dentro de `DNA1`, los bloques `NAME` y `TYPE` llevan un
contador delante, pero **`TLEN` no** —usa el de `TYPE`—. Leerlo como si lo tuviera
desplaza cuatro bytes todo lo que viene detrás y el fichero deja de tener sentido.

`tools/blend_a_glb.py` lo convierte a GLB, y hace por el camino lo que hacía falta:

- **Ejes de Blender (Z arriba) a los de three.js (Y arriba).**
- **Suelda vértices repetidos.** En este modelo bajó de 688.267 a 128.371.
- **Compacta.** Al descartar piezas quedan vértices que ya no usa ningún triángulo, y
  ocupan 12 bytes cada uno: sin compactar, quitar los asientos solo bajaba de 9,5 a
  9,5 MB; con compactación, a 3,5.
- **Endereza por el cuenco, no por la caja envolvente.** Primero lo hice por la caja y
  salió mal: la explanada exterior tiene su propia orientación y arrastraba el resultado,
  con lo que el campo quedaba girado 35° y descentrado dentro del estadio. Lo que sí
  define el estadio es el borde interior del graderío: se recorre en 240 sectores
  quedándose con el punto más cercano al centro de cada uno —eso dibuja el óvalo de la
  primera fila— y de esa nube salen el centro y el eje mayor.
- **Se calibra con el césped del modelo, no con el hueco.** El hueco del cuenco incluye
  la pista de atletismo, así que ajustar contra él dejaba el campo enorme. El modelo trae
  un material `Grass_002` que **es** el césped: se escala para que mida 105 m y se baja a
  cota cero. Así el nuestro cae encima por construcción, no por tanteo.
- **Una primitiva por material**, para poder colorear cada pieza.

### Por qué no se usan las texturas

Vienen en un `Texture.rar`, pero **no sirven**. El `.blend` referencia **12 imágenes
externas** y ninguna va empotrada dentro del fichero; el RAR trae **4**, y solo **2
coinciden** (`fmrf.jpg` y `seats.png`). Las otras dos del RAR (`AVSF.jpg`, `fsa.jpg`) no
las pide el modelo, y faltan 10 de las que sí pide:

```
//bench/Carpet_Aqua1.jpg     //bench/Couro_Azul.jpg      //bench/Logo.png
//bench/Carpet_Frieze_Blue.jpg  //bench/Couro_branco.jpg  //bench/SerrArena_letreiro1.png
//bench/Phoenix_Civic_Plaza_31.jpg   //IMG-2674.PNG   //MADE BY.psd   //Untitled-1.jpg
```

Además, las siete que el sistema de materiales enlaza son todas del **banquillo**
(`bench/`), no de las gradas; y `seats.png`, que sería la que se notaría, va por árbol de
nodos sobre el material `Seat`, que son los 340.000 triángulos que se descartan.

Con esto no hay textura que poner. Para tenerlas hacen falta los ficheros que faltan, o
—mejor— un GLB exportado desde Blender con **File → External Data → Pack Resources** y
las imágenes empotradas.

Lo que sí se puede sin ninguna textura: **repartir el hormigón por geometría**. El
graderío y los muros vienen con el mismo material `Cement`, así que por nombre no se
pueden pintar distinto; lo que los separa es hacia dónde miran. `--repartir Cement,Wall,
Aliminuim` los parte en `Cement:grada`, `Cement:cubierta`… y la paleta los pinta aparte.
Con eso las gradas parecen gradas —53.790 triángulos de graderío frente a 11.740 de
fachada— y el estadio deja de ser un bloque de hormigón blanco.

Tres cosas que hubo que averiguar mirando la geometría, porque el fichero no las dice:

| | |
|---|---|
| El césped del modelo no está a cero | Está a **14,5 m**: el material `marking` (las líneas del campo) delata la altura. `--baja 14.5` |
| Hay geometría suelta | `Plane.008` medía 522 m de largo, fuera del estadio. `--sin-objetos` |
| Los asientos son el 62 % de todo | 340.000 de 516.000 triángulos, y su color venía de `seats.png`, no del material: sin textura habrían salido grises igual. Se descartan y quedan las gradas debajo |

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
- **Nada de encender y apagar en seco.** El primer intento ocultaba la etiqueta con un
  booleano, y al girar la cámara el borde del dorsal se cruzaba una y otra vez: parpadeo.
  Dos cosas lo quitan: **histéresis** —una vez apagada hace falta despejar 10 px de más
  para volver, así que medio grado de giro ya no la enciende y la apaga— y un **fundido
  de 160 ms** en vez de un salto. Además solo cuentan los dorsales que están medio metro
  más cerca: a igual profundidad el orden baila.
- **Una etiqueta tampoco puede tapar el dorsal de quien está delante.** Es el mismo
  problema —el HTML va siempre por encima del lienzo— pero al revés: el nombre de uno del
  fondo se plantaba sobre el número de uno de delante, que es lo que lo identifica. Se
  comprueba en pantalla: si el centro de un dorsal más cercano cae dentro del rectángulo
  de una etiqueta, esa etiqueta se calla. Solo cuando lo cubre de verdad, no al rozarlo:
  medido, silencia 1 de 22 en «Once local» y 3 en «Campo completo», y ninguna en las
  vistas cenital y a ras.
- **Las etiquetas HTML no las tapa nada, y con estadio se nota.** Los dorsales son
  geometría y el buffer de profundidad los oculta solo; los nombres son DOM y se quedaban
  flotando sobre la grada al mirar el estadio desde fuera. Se comprueba la línea de visión
  contra un **muro invisible con la forma del cuenco** —cuatro cuadros inclinados, del
  borde interior de la grada al alero, medidos sobre el propio modelo—: 22 rayos contra 8
  triángulos por cuadro. Contra el estadio de verdad serían 22 rayos contra 48.916
  triángulos, que no cabe en un cuadro a 60 fps.
  Comprobado: desde arriba y fuera 22/22 etiquetas, desde fuera y a ras 0/22, dentro 22/22.
- **`A ras de césped` se mete dentro del campo cuando hay estadio.** A 47 m del eje la
  cámara queda metida en el graderío; con estadio esa vista pasa a 32 m, que es la banda.
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
| 60 fps y menos de 60 llamadas de dibujo | ✅ **19 llamadas** con el campo suelto, 27 con estadio, mapa de calor y flujo a la vez |
| Sin ningún binario de modelo en el repo | ✅ |
| Funciona con el dedo | 🟡 puesto y con eventos de puntero; **sin probar en un móvil real** |

## Lo que falta

- **El mapa de tiros sobre el campo 3D.** Los datos ya están incrustados (51 tiros con
  coordenada de origen y xG); en la ficha salen como lista, pero no dibujados. El mapa de
  calor ya está sobre el césped, así que la capa y la rampa se reutilizan.
- **El sentido de los pases sobre el campo.** El dato está (la matriz es dirigida) y en la
  ficha se ve; en el campo haría falta algo que se lea sin explicación, tipo dos cintas
  paralelas, no una que se estrecha.
- **El estadio con más de un material.** Ahora va todo del mismo hormigón; separar grada,
  cubierta y torres de luz es cuestión de conservar los grupos del OBJ al convertir.
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

# BeSoccer · Campo 3D

Visor 3D interactivo de alineaciones, como paso previo a una app para Apple Vision Pro.
**Toda la geometría se genera por código**: no hay ni un `.glb`, ni un `.fbx`, ni ninguna
textura descargada. El campo es reglamento FIFA dibujado sobre un canvas.

**Estado: completo (fases 1 y 2).** Campo, cámara, 22 jugadores, selección y ficha.

> **Los datos son de muestra.** El partido, las alineaciones, las notas, las
> estadísticas y los mapas de calor están inventados. Sirven para decidir jerarquía,
> copy y estados; no para leer nada. Están todos en `PARTIDO`, al principio del fichero.

## Abrirlo

```bash
open index.html                  # doble clic vale: no hay build ni npm
python3 -m http.server 8000      # para probarlo en un móvil de verdad
```

Necesita red la primera vez: three.js viene de jsDelivr con la versión fijada
(`three@0.186.0`), resuelto con un `<script type="importmap">`.

### Enlaces directos

Para dejar preparado un ángulo o una ficha en una presentación:

| Parámetro | Qué hace |
|---|---|
| `?vista=` | `completo` · `local` · `visita` · `tactica` · `ras` |
| `?jugador=` | `l7` (local, dorsal 7) · `v10` (visitante, dorsal 10) |
| `?etiquetas=0` `?dorsales=0` `?pases=1` | estado inicial de los interruptores |
| `?debug` | fps, llamadas de dibujo y triángulos (también con la tecla **D**) |

Ejemplo: `index.html?vista=tactica&pases=1&etiquetas=0` deja la forma de los dos equipos.

### Cómo se usa

Arrastrar orbita · rueda o pinza acerca · botón derecho o dos dedos desplaza ·
clic o toque en un jugador abre su ficha · **← →** cambia de jugador · **Esc** cierra.

## Lo que hay dentro

Un solo `index.html`, en bloques numerados:

| Bloque | Qué contiene |
|---|---|
| 1 · Medidas | `M`: reglamento FIFA en metros. **1 unidad de three = 1 metro.** |
| 1 bis · El partido | `PARTIDO`: competición, marcador, sucesos y los 22 jugadores |
| 2 · Renderizador | WebGL2, ACESFilmic, `RoomEnvironment` para el reflejo ambiental, una luz direccional |
| 3 · El campo | textura de césped y líneas, zócalo, sombra de contacto, porterías, banderines |
| 3 bis · Los jugadores | fichas, dorsales en billboard, etiquetas HTML, líneas de pase |
| 4 · Cámara | `OrbitControls` con límites, encuadre calculado y puntos de vista con transición |
| 5 · Interfaz | cabecera, interruptores, selección, ficha del jugador, mapa de calor |
| 6 · Bucle | render, redimensionado y contador de rendimiento |

Cambiar una medida en `M` cambia el campo entero: las líneas se dibujan de ahí.
Cambiar `PARTIDO` cambia el partido: nada más lee esos datos.

## Decisiones que conviene no deshacer

### El campo

- **Las líneas son textura, no geometría.** Se dibujan sobre un canvas 2D de 4096 px
  (~35 px/m, así una línea de 12 cm cae en 4 px) y se usan como mapa del césped. Sale
  más nítido, más barato y se retoca sin tocar la escena.
- **El césped no lleva ruido por píxel.** Lleva manchas grandes. El ruido fino en una
  textura de 4096 px hace moiré en cuanto el campo se ve de lejos.
- **El zócalo tiene la tapa 5 cm por debajo del césped.** Dos caras a la misma cota,
  vistas a 130 m, se pelean por la profundidad y el zócalo aparece atravesando el campo
  en diagonal. Por lo mismo el plano cercano de la cámara está a 2 m y no a 0,5.
- **La sombra de contacto es una textura, no una luz.** Es lo que hace que el campo
  parezca apoyado en algo en vez de flotando. Cuesta una llamada de dibujo.
- **Sin estadio, y a propósito.** La grada es un modelo de Blender, y es donde se van el
  tiempo y los megas. Si algún día se añade, la más cercana a la cámara se oculta o se
  baja, para que el césped nunca quede tapado. Y en unas gafas el estadio es la
  habitación del usuario.

### La cámara

- **La distancia no se escribe a mano, se calcula.** `distanciaEncuadre()` proyecta las
  ocho esquinas de la losa y busca la distancia a la que caben todas. Una distancia fija
  se queda corta en cuanto cambia la proporción de la pantalla; en vertical, además, el
  encuadre gira 90° para que los 105 m caigan sobre el lado largo.
- **La inercia no es un adorno.** `enableDamping` con `dampingFactor 0.05` es la mitad
  de la sensación de calidad; sin ella parece un visor técnico.
- **El objetivo no se va.** Se orbita alrededor del campo, no se navega por la escena. El
  botón derecho desplaza, pero con correa: el objetivo no puede salir del campo.
- **`A ras de césped` suelta el límite polar** a 1,555 rad. Con el tope normal de 1,45,
  mirando casi horizontal, `OrbitControls` devolvía la cámara hacia arriba.
- **Auto-rotar se para al tocar y no vuelve solo.** Vende en una demo y no molesta al usar.

### Los jugadores

- **Sombra, disco y poste van en `InstancedMesh`:** una llamada de dibujo cada una para
  los 22, no veintidós.
- **El dorsal es un atlas de texturas y 22 cuadros en una sola malla.** Las UV apuntan a
  su celda y no cambian; lo que se reescribe cada cuadro son las posiciones, orientadas
  con los ejes de la cámara. Eso es el billboard, y cuesta una llamada.
- **Los cuadros se ordenan de lejos a cerca cada cuadro.** Sin ordenar, dos dorsales que
  se solapan se mezclan en el orden equivocado y el de detrás tapa al de delante.
- **El atlas se dibuja después de `document.fonts.load`,** con tope de 2,5 s. Si se
  dibuja antes, los números salen en la tipografía de reserva; con el tope, si Google
  Fonts no contesta el prototipo arranca igual.
- **El nombre va en HTML (`CSS2DRenderer`), nunca en textura.** Se lee nítido a cualquier
  distancia, se estila con el CSS de la casa y es accesible. La etiqueta lleva los colores
  de la equipación, que es lo que distingue equipo de un vistazo.
- **El clic va contra el disco Y contra el dorsal.** El blanco principal es el disco, como
  pide el encargo, pero la etiqueta lo tapa: si solo respondiera el disco, tocar el nombre
  no haría nada. Las etiquetas HTML no son blanco de nada (`pointer-events:none`).
- **Un arrastre orbita, solo un toque limpio selecciona.** Umbral de 6 px entre el
  `pointerdown` y el `pointerup`. Sin eso, cada giro que empiece sobre un jugador abre su
  ficha.
- **La intensidad del mapa de calor se lee del canal ALFA.** El lienzo guarda el color
  premultiplicado y `getImageData` lo devuelve desmultiplicado, así que el rojo de una
  mancha blanca vuelve a 255 en toda ella y el mapa sale plano. Y se normaliza por el
  máximo real: con un divisor fijo se satura y el campo entero acaba en rojo.
- **Las estadísticas se generan con un PRNG sembrado con el id del jugador.** El mismo
  jugador da siempre los mismos números: un prototipo que cambia de cifras al recargar no
  se puede enseñar dos veces.

### Honestidad de los datos

- **«Líneas de pase» no son pases.** Es un grafo de proximidad: cada jugador con sus tres
  compañeros más cercanos, hasta 26 m. Dibuja la forma del equipo. Con datos reales de
  pases se sustituye `lineasDePase()` y nada más.
- **Los escudos son marcadores de posición** (la sigla sobre el color de la camiseta), no
  los escudos de verdad.
- **Faltan tres puntos de vista del documento de encargo**: *Forma ofensiva*, *Forma
  defensiva* y *Balón parado*. No están porque no son ángulos de cámara: son tres juegos
  alternativos de posiciones, y habría que inventárselos. Cuando haya datos tácticos
  reales, son tres entradas más en `VISTAS` con su propio `PARTIDO.jugadores`.

## Criterios de aceptación

| | |
|---|---|
| Bundle propio < 300 KB | ✅ 73 KB (+ three desde CDN y Asap desde Google Fonts) |
| Orbitar 360° arrastrando | ✅ |
| Cenital ↔ ras de césped con transición | ✅ 700 ms, `easeInOutCubic` |
| Clic en jugador: se eleva, anillo y ficha | ✅ probado con eventos sintéticos |
| Etiquetas legibles a cualquier ángulo, nunca del revés | ✅ HTML, ordenadas por profundidad |
| `InstancedMesh` para los 22 discos y los 22 postes | ✅ |
| 60 fps y menos de 60 llamadas de dibujo | ✅ **17 llamadas**, 7,7k triángulos |
| Sin ningún binario de modelo en el repo | ✅ |
| Funciona con el dedo | 🟡 `OrbitControls` y `touch-action:none` puestos, y el toque
  usa eventos de puntero; **sin probar en un móvil real** |

Lo que se ha comprobado con capturas y con eventos sintéticos: encuadre en apaisado y en
vertical, las cinco vistas, el hover, tres clics seguidos, que un arrastre no selecciona,
que el clic en césped vacío cierra la ficha, y el teclado (← → y Esc).

## El puente a las gafas

Safari en visionOS ejecuta WebXR, y three.js lo soporta. Con `renderer.xr.enabled`, el
`VRButton` y el campo escalado a tamaño de mesa (factor ~0,02), este mismo fichero
servido por HTTPS se abre en el Vision Pro sin escribir una línea de Swift. Habrá que
sustituir `OrbitControls` por manipulación directa —agarrar el campo y girarlo con las
manos— y medir el coste del estéreo, que dobla el trabajo del render. Las etiquetas HTML
de `CSS2DRenderer` **no** sobreviven al modo inmersivo: ahí los nombres tendrían que
pasar a textura o a un plano de tres.

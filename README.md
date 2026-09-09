# BeSoccer · Campo 3D

Visor 3D interactivo de alineaciones, como paso previo a una app para Apple Vision Pro.
**Toda la geometría se genera por código**: no hay ni un `.glb`, ni un `.fbx`, ni ninguna
textura descargada. El campo es reglamento FIFA dibujado sobre un canvas.

**Estado: fase 1 de 2.** Campo y cámara. Los 22 jugadores llegan en la fase 2.

## Abrirlo

```bash
open index.html                  # doble clic vale: no hay build ni npm
python3 -m http.server 8000      # para probarlo en un móvil de verdad
```

Necesita red la primera vez: three.js viene de jsDelivr con la versión fijada
(`three@0.186.0`), resuelto con un `<script type="importmap">`.

### Enlaces directos a un ángulo

`?vista=completo` · `?vista=local` · `?vista=visita` · `?vista=tactica` · `?vista=ras`
Y `?debug` (o la tecla **D**) enseña fps, llamadas de dibujo y triángulos.

## Lo que hay dentro

Un solo `index.html`, en bloques numerados:

| Bloque | Qué contiene |
|---|---|
| 1 · Medidas | `M`: reglamento FIFA en metros. **1 unidad de three = 1 metro.** |
| 2 · Renderizador | WebGL2, ACESFilmic, `RoomEnvironment` para el reflejo ambiental, una luz direccional |
| 3 · El campo | textura de césped y líneas, zócalo, sombra de contacto, porterías, banderines |
| 4 · Cámara | `OrbitControls` con límites, encuadre calculado y puntos de vista con transición |
| 5 · Interfaz | interruptores, pastillas, barra flotante |
| 6 · Bucle | render, redimensionado y contador de rendimiento |

Cambiar una medida en `M` cambia el campo entero: las líneas se dibujan de ahí.

## Decisiones que conviene no deshacer

- **Las líneas son textura, no geometría.** Se dibujan sobre un canvas 2D de 4096 px
  (~35 px/m, así una línea de 12 cm cae en 4 px) y se usan como mapa del césped. Sale
  más nítido, más barato y se retoca sin tocar la escena.
- **El césped no lleva ruido por píxel.** Lleva manchas grandes. El ruido fino en una
  textura de 4096 px hace moiré en cuanto el campo se ve de lejos.
- **El zócalo tiene la tapa 5 cm por debajo del césped.** Dos caras a la misma cota,
  vistas a 130 m, se pelean por la profundidad y el zócalo aparece atravesando el campo
  en diagonal. Por lo mismo el plano cercano de la cámara está a 2 m y no a 0,5.
- **La distancia de cámara no se escribe a mano, se calcula.** `distanciaEncuadre()`
  proyecta las ocho esquinas de la losa y busca la distancia a la que caben todas. Una
  distancia fija se queda corta en cuanto cambia la proporción de la pantalla; en
  vertical, además, el encuadre gira 90° para que los 105 m caigan sobre el lado largo.
- **La inercia no es un adorno.** `enableDamping` con `dampingFactor 0.05` es la mitad
  de la sensación de calidad; sin ella parece un visor técnico.
- **El objetivo de la cámara no se va.** Se orbita alrededor del campo, no se navega por
  la escena. El botón derecho desplaza, pero con correa: el objetivo no puede salir del
  campo.
- **La sombra de contacto es una textura, no una luz.** Es lo que hace que el campo
  parezca apoyado en algo en vez de flotando. Cuesta una llamada de dibujo.
- **Sin estadio, y a propósito.** La grada es un modelo de Blender, y es donde se van el
  tiempo y los megas. Si algún día se añade, la más cercana a la cámara se oculta o se
  baja, para que el césped nunca quede tapado. Y en unas gafas el estadio es la
  habitación del usuario.
- **Auto-rotar se para al tocar y no vuelve solo.** Vende en una demo y no molesta al usar.
- **Doce llamadas de dibujo.** Los 22 tubos de las dos porterías van fusionados en una
  malla, y los banderines en `InstancedMesh`. El margen es para los jugadores.

## Criterios de aceptación

| | |
|---|---|
| Bundle propio < 300 KB | ✅ 37 KB (+ three desde CDN y Asap desde Google Fonts) |
| Orbitar 360° arrastrando | ✅ |
| Cenital ↔ ras de césped con transición | ✅ 700 ms, `easeInOutCubic` |
| Sin ningún binario de modelo en el repo | ✅ |
| Clic en jugador: ficha y panel | ⏳ fase 2 |
| Etiquetas legibles a cualquier ángulo | ⏳ fase 2 (`CSS2DRenderer` ya montado) |
| Funciona con el dedo | 🟡 `OrbitControls` y `touch-action:none` puestos; **sin probar en un móvil real** |

## Fase 2

22 fichas desde `match.json` (disco a ras de césped, poste corto, dorsal en billboard),
etiqueta HTML con `CSS2DRenderer`, sombra elíptica, raycasting sobre los discos,
selección que eleva la ficha 0,4 m, panel de jugador, cabecera de marcador y los tres
puntos de vista que faltan (forma ofensiva, defensiva, balón parado).

## El puente a las gafas

Safari en visionOS ejecuta WebXR, y three.js lo soporta. Con `renderer.xr.enabled`, el
`VRButton` y el campo escalado a tamaño de mesa (factor ~0,02), este mismo fichero
servido por HTTPS se abre en el Vision Pro sin escribir una línea de Swift. Habrá que
sustituir `OrbitControls` por manipulación directa y medir el coste del estéreo, que
dobla el trabajo del render.

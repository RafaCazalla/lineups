#!/usr/bin/env python3
"""OBJ de 3ds Max -> GLB compacto, sin dependencias.

    python3 tools/obj_a_glb.py "campo 3d/3d-model.obj" -o assets/estadio.glb

Por qué no se sirve el OBJ tal cual: son 4,2 MB de texto, hay que analizarlo en
el navegador y arrastra un .mtl con diez colores de alambre de 3ds Max que no
significan nada. Aquí sale una sola malla indexada con posiciones y nada más:
las normales no hacen falta porque el material se pinta con `flatShading`, que
las calcula en el fragmento. De 4,2 MB de texto a ~600 KB binarios.

Lo que se hornea en el fichero, para que la escena no tenga que corregirlo:
  · milímetros -> metros
  · el suelo del modelo baja a y = 0
  · centrado en x y z
  · giro de 90° para que el lado largo caiga sobre el eje x, como nuestro campo
"""
import argparse, json, struct, sys
from collections import Counter


def leer_obj(ruta):
    V, F = [], []
    for ln in open(ruta, encoding='utf-8', errors='replace'):
        if ln.startswith('v '):
            V.append([float(x) for x in ln.split()[1:4]])
        elif ln.startswith('f '):
            # «f v/vt/vn» -> solo interesa el índice de vértice, y es 1-based.
            idx = [int(t.split('/')[0]) - 1 for t in ln.split()[1:]]
            if len(idx) < 3:
                continue                      # hay caras de 1 y 2 vértices: basura
            for k in range(1, len(idx) - 1):  # abanico: vale para quads y n-gons
                F.append((idx[0], idx[k], idx[k + 1]))
    return V, F


def glb(V, F):
    """Un GLB mínimo: un accessor de posiciones, uno de índices, una malla."""
    n = len(V)
    tipo_idx, fmt = (5123, '<H') if n <= 65535 else (5125, '<I')
    pos = bytearray()
    mn = [min(p[i] for p in V) for i in range(3)]
    mx = [max(p[i] for p in V) for i in range(3)]
    for p in V:
        pos += struct.pack('<3f', *p)
    idx = bytearray()
    for t in F:
        for i in t:
            idx += struct.pack(fmt, i)
    while len(idx) % 4:                       # los buffer views van alineados a 4
        idx += b'\x00'

    bin_ = bytes(pos) + bytes(idx)
    doc = {
        'asset': {'version': '2.0', 'generator': 'obj_a_glb.py de besoccer-campo-3d'},
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'mesh': 0, 'name': 'estadio'}],
        'meshes': [{'primitives': [{'attributes': {'POSITION': 0}, 'indices': 1}]}],
        'buffers': [{'byteLength': len(bin_)}],
        'bufferViews': [
            {'buffer': 0, 'byteOffset': 0, 'byteLength': len(pos), 'target': 34962},
            {'buffer': 0, 'byteOffset': len(pos), 'byteLength': len(idx), 'target': 34963},
        ],
        'accessors': [
            {'bufferView': 0, 'componentType': 5126, 'count': n, 'type': 'VEC3',
             'min': mn, 'max': mx},
            {'bufferView': 1, 'componentType': tipo_idx, 'count': len(F) * 3, 'type': 'SCALAR'},
        ],
    }
    js = json.dumps(doc, separators=(',', ':')).encode('utf-8')
    js += b' ' * (-len(js) % 4)
    trozos = struct.pack('<II', len(js), 0x4E4F534A) + js \
           + struct.pack('<II', len(bin_), 0x004E4942) + bin_
    return struct.pack('<III', 0x46546C67, 2, 12 + len(trozos)) + trozos


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('obj')
    ap.add_argument('-o', '--salida', required=True)
    ap.add_argument('--escala', type=float, default=0.001, help='milímetros a metros')
    ap.add_argument('--suelo', type=float, default=None,
                    help='altura del suelo en unidades del modelo; si no, la más repetida')
    ap.add_argument('--giro', type=int, default=90, choices=[0, 90, 180, 270],
                    help='giro en grados sobre y, para poner el lado largo en x')
    a = ap.parse_args()

    V, F = leer_obj(a.obj)
    if not V or not F:
        sys.exit('El OBJ no trae geometría utilizable.')

    # El suelo del modelo no está en y=0: se busca la altura con más vértices,
    # que en un estadio es el plano del terreno.
    suelo = a.suelo
    if suelo is None:
        suelo = Counter(round(p[1]) for p in V).most_common(1)[0][0]

    cx = (min(p[0] for p in V) + max(p[0] for p in V)) / 2
    cz = (min(p[2] for p in V) + max(p[2] for p in V)) / 2
    s = a.escala
    giros = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}
    co, si = giros[a.giro]
    W = []
    for x, y, z in V:
        x, y, z = (x - cx) * s, (y - suelo) * s, (z - cz) * s
        W.append([x * co + z * si, y, -x * si + z * co])

    datos = glb(W, F)
    open(a.salida, 'wb').write(datos)
    t = [round(max(p[i] for p in W) - min(p[i] for p in W), 2) for i in range(3)]
    print(f'{a.salida}: {len(datos)/1024:.0f} KB · {len(W)} vértices · {len(F)} triángulos')
    print(f'suelo del modelo en y={suelo} · tamaño final {t[0]} x {t[1]} x {t[2]} m'
          f' · altura {round(min(p[1] for p in W),2)} a {round(max(p[1] for p in W),2)}')


if __name__ == '__main__':
    main()

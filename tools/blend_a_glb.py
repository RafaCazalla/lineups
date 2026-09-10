#!/usr/bin/env python3
"""Escena de Blender (.blend) -> GLB compacto, sin Blender y sin dependencias.

    python3 tools/blend_a_glb.py "tanger 3d/Stad de tanger.blend" -o assets/tanger.glb

Un .blend es autodescriptivo —lleva dentro la definición de sus propias
estructuras en el bloque DNA1—, así que se puede leer sin tener Blender
instalado. `tools/blend.py` hace esa lectura; aquí se saca lo que necesita la
web: mallas con su matriz de objeto, agrupadas por material, y el color de cada
material.

Lo que se hace por el camino:
  · ejes de Blender (Z arriba) a los de three.js (Y arriba)
  · se sueldan los vértices repetidos, que en un modelo exportado son muchos
  · unidades a metros, suelo a y = 0, centrado, y el lado largo sobre el eje x
  · una primitiva por material, para poder colorear cada pieza por separado

No se leen texturas ni UVs: para el prototipo basta el color plano del material,
y una textura por pieza multiplicaría el peso del fichero.
"""
import argparse, json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blend import Blend


def leer_escena(bl, escala_soldadura, sin_objetos=()):
    cid = bl.campos(bl.por_nombre['ID'])
    cob = bl.campos(bl.por_nombre['Object'])
    cme = bl.campos(bl.por_nombre['Mesh'])
    cmv = bl.campos(bl.por_nombre['MVert'])
    cmp_ = bl.campos(bl.por_nombre['MPoly'])
    cml = bl.campos(bl.por_nombre['MLoop'])
    cma = bl.campos(bl.por_nombre['Material'])
    tmv, tmp, tml = (bl.tlen[bl.estructuras[bl.por_nombre[t]][0]]
                     for t in ('MVert', 'MPoly', 'MLoop'))

    def nombre(base):
        o = cid['name'][0]
        return bl.d[base + o:base + o + 66].split(b'\0')[0].decode('latin1')[2:]

    verts, tris_por_mat, colores = [], {}, {}
    indice = {}                      # coordenada redondeada -> índice de vértice
    q = 1.0 / escala_soldadura

    for ob in bl.de_codigo('OB'):
        if bl.leer(ob['ini'], cob, 'type') != 1:        # 1 = malla
            continue
        if nombre(ob['ini']) in sin_objetos:
            continue
        bme = bl.bloque_en(bl.leer(ob['ini'], cob, 'data'))
        if not bme or bme['code'] != 'ME':
            continue
        base = bme['ini']
        nv = bl.leer(base, cme, 'totvert') or 0
        npo = bl.leer(base, cme, 'totpoly') or 0
        if not nv or not npo:
            continue
        bv = bl.bloque_en(bl.leer(base, cme, 'mvert'))
        bp = bl.bloque_en(bl.leer(base, cme, 'mpoly'))
        blo = bl.bloque_en(bl.leer(base, cme, 'mloop'))
        if not (bv and bp and blo):
            continue

        # Materiales de la malla: un array de punteros a Material.
        mats, ncol = [], bl.leer(base, cme, 'totcol') or 0
        bmat = bl.bloque_en(bl.leer(base, cme, 'mat'))
        if bmat and ncol:
            fmt = 'Q' if bl.p == 8 else 'I'
            for k in range(ncol):
                pm = struct.unpack_from(bl.orden + fmt, bl.d, bmat['ini'] + k * bl.p)[0]
                bm = bl.bloque_en(pm)
                if bm and bm['code'] == 'MA':
                    nm = nombre(bm['ini'])
                    colores.setdefault(nm, [round(bl.leer(bm['ini'], cma, c), 4)
                                            for c in 'rgb'] + [1])
                    mats.append(nm)
                else:
                    mats.append('sin material')
        if not mats:
            mats = ['sin material']
            colores.setdefault('sin material', [0.8, 0.8, 0.8, 1])

        # obmat de Blender: las tres primeras columnas son los ejes y la cuarta
        # la traslación.
        m = bl.leer(ob['ini'], cob, 'obmat', 16)

        def coloca(x, y, z):
            wx = m[0] * x + m[4] * y + m[8] * z + m[12]
            wy = m[1] * x + m[5] * y + m[9] * z + m[13]
            wz = m[2] * x + m[6] * y + m[10] * z + m[14]
            return (wx, wz, -wy)          # Z arriba (Blender) -> Y arriba (three)

        # Vértices de esta malla, soldando repetidos contra el índice global.
        locales = [0] * nv
        off_co = cmv['co'][0]
        for i in range(nv):
            x, y, z = struct.unpack_from(bl.orden + '3f', bl.d, bv['ini'] + i * tmv + off_co)
            p = coloca(x, y, z)
            k = (int(p[0] * q), int(p[1] * q), int(p[2] * q))
            j = indice.get(k)
            if j is None:
                j = len(verts)
                indice[k] = j
                verts.append(p)
            locales[i] = j

        off_ls, off_tl, off_mn = cmp_['loopstart'][0], cmp_['totloop'][0], cmp_['mat_nr'][0]
        off_v = cml['v'][0]
        for i in range(npo):
            o = bp['ini'] + i * tmp
            ls = struct.unpack_from(bl.orden + 'i', bl.d, o + off_ls)[0]
            tl = struct.unpack_from(bl.orden + 'i', bl.d, o + off_tl)[0]
            mn = struct.unpack_from(bl.orden + 'h', bl.d, o + off_mn)[0]
            if tl < 3:
                continue
            idx = [locales[struct.unpack_from(bl.orden + 'i', bl.d,
                   blo['ini'] + (ls + k) * tml + off_v)[0]] for k in range(tl)]
            mat = mats[mn] if 0 <= mn < len(mats) else mats[0]
            lista = tris_por_mat.setdefault(mat, [])
            for k in range(1, tl - 1):     # abanico: vale para quads y n-gons
                a, b, c = idx[0], idx[k], idx[k + 1]
                if a != b and b != c and a != c:      # fuera degenerados
                    lista.append((a, b, c))
    return verts, tris_por_mat, colores


def listar_objetos(bl, giro):
    """Cada objeto con su tamaño y a qué distancia del centro está. Sirve para
    separar el estadio de lo que le rodea: explanadas, calles, aparcamientos."""
    import math
    cid = bl.campos(bl.por_nombre['ID'])
    cob = bl.campos(bl.por_nombre['Object'])
    cme = bl.campos(bl.por_nombre['Mesh'])
    cmv = bl.campos(bl.por_nombre['MVert'])
    tmv = bl.tlen[bl.estructuras[bl.por_nombre['MVert']][0]]
    ang = math.radians(giro); co, si = math.cos(ang), math.sin(ang)
    filas = []
    for ob in bl.de_codigo('OB'):
        if bl.leer(ob['ini'], cob, 'type') != 1:
            continue
        bme = bl.bloque_en(bl.leer(ob['ini'], cob, 'data'))
        if not bme or bme['code'] != 'ME':
            continue
        nv = bl.leer(bme['ini'], cme, 'totvert') or 0
        bv = bl.bloque_en(bl.leer(bme['ini'], cme, 'mvert'))
        if not nv or not bv:
            continue
        m = bl.leer(ob['ini'], cob, 'obmat', 16)
        off = cmv['co'][0]
        paso = max(1, nv // 1500)
        pts = []
        for i in range(0, nv, paso):
            x, y, z = struct.unpack_from(bl.orden + '3f', bl.d, bv['ini'] + i * tmv + off)
            wx = m[0]*x + m[4]*y + m[8]*z + m[12]
            wy = m[1]*x + m[5]*y + m[9]*z + m[13]
            wz = m[2]*x + m[6]*y + m[10]*z + m[14]
            X, Y, Z = wx, wz, -wy                     # Z arriba -> Y arriba
            pts.append((X * co + Z * si, Y, -X * si + Z * co))
        o = cid['name'][0]
        nom = bl.d[ob['ini']+o:ob['ini']+o+66].split(b'\0')[0].decode('latin1')[2:]
        filas.append((nom, nv, pts))
    # Centro común, del conjunto
    tx = [p[0] for _, _, ps in filas for p in ps]
    tz = [p[2] for _, _, ps in filas for p in ps]
    cx, cz = (min(tx)+max(tx))/2, (min(tz)+max(tz))/2
    print(f"{'objeto':<26}{'verts':>8}{'radio min':>11}{'radio max':>11}{'y min':>8}{'y max':>8}")
    for nom, nv, ps in sorted(filas, key=lambda f: -max(math.hypot(p[0]-cx, p[2]-cz) for p in f[2])):
        rs = [math.hypot(p[0]-cx, p[2]-cz) for p in ps]
        ys = [p[1] for p in ps]
        print(f'{nom:<26}{nv:>8}{min(rs):>11.0f}{max(rs):>11.0f}{min(ys):>8.1f}{max(ys):>8.1f}')


def glb(V, grupos, colores):
    n = len(V)
    corto = n <= 65535
    tipo_idx, fmt = (5123, '<H') if corto else (5125, '<I')
    pos = bytearray()
    mn = [min(p[i] for p in V) for i in range(3)]
    mx = [max(p[i] for p in V) for i in range(3)]
    for p in V:
        pos += struct.pack('<3f', *p)

    vistas = [{'buffer': 0, 'byteOffset': 0, 'byteLength': len(pos), 'target': 34962}]
    accs = [{'bufferView': 0, 'componentType': 5126, 'count': n, 'type': 'VEC3',
             'min': mn, 'max': mx}]
    idx_todo, prims, mats = bytearray(), [], []
    for nombre in sorted(grupos, key=lambda k: -len(grupos[k])):
        F = grupos[nombre]
        if not F:
            continue
        ini = len(idx_todo)
        for t in F:
            for i in t:
                idx_todo += struct.pack(fmt, i)
        while len(idx_todo) % 4:
            idx_todo += b'\x00'
        vistas.append({'buffer': 0, 'byteOffset': len(pos) + ini,
                       'byteLength': len(F) * 3 * (2 if corto else 4), 'target': 34963})
        accs.append({'bufferView': len(vistas) - 1, 'componentType': tipo_idx,
                     'count': len(F) * 3, 'type': 'SCALAR'})
        prims.append({'attributes': {'POSITION': 0}, 'indices': len(accs) - 1,
                      'material': len(mats)})
        mats.append({'name': nombre,
                     'pbrMetallicRoughness': {
                         'baseColorFactor': colores.get(nombre, [0.8, 0.8, 0.8, 1]),
                         'metallicFactor': 0.0, 'roughnessFactor': 0.85}})

    bin_ = bytes(pos) + bytes(idx_todo)
    doc = {'asset': {'version': '2.0', 'generator': 'blend_a_glb.py de besoccer-campo-3d'},
           'scene': 0, 'scenes': [{'nodes': [0]}],
           'nodes': [{'mesh': 0, 'name': 'estadio'}],
           'meshes': [{'primitives': prims}], 'materials': mats,
           'buffers': [{'byteLength': len(bin_)}],
           'bufferViews': vistas, 'accessors': accs}
    js = json.dumps(doc, separators=(',', ':')).encode('utf-8')
    js += b' ' * (-len(js) % 4)
    trozos = struct.pack('<II', len(js), 0x4E4F534A) + js \
           + struct.pack('<II', len(bin_), 0x004E4942) + bin_
    return struct.pack('<III', 0x46546C67, 2, 12 + len(trozos)) + trozos


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('blend')
    ap.add_argument('-o', '--salida', required=True)
    ap.add_argument('--escala', type=float, default=1.0, help='a metros')
    ap.add_argument('--baja', type=float, default=0.0,
                    help='metros a restar en y tras escalar; sirve para poner el césped '
                         'del modelo a la altura cero (el suelo del fichero no suele serlo)')
    ap.add_argument('--ajustar-hueco', type=float, default=0.0,
                    help='metros que debe medir el hueco interior del cuenco a lo largo; '
                         'la escala se calcula sola para que el campo quepa')
    ap.add_argument('--soldadura', type=float, default=0.001,
                    help='vértices más cerca que esto se funden, en unidades del fichero')
    ap.add_argument('--giro', type=int, default=0, choices=[0, 90, 180, 270])
    ap.add_argument('--giro-fino', type=float, default=-1.0,
                    help='giro en grados sobre y, para enderezar un modelo torcido')
    ap.add_argument('--fuera', default='', help='materiales a descartar, separados por coma')
    ap.add_argument('--sin-objetos', default='',
                    help='objetos a descartar por nombre, separados por coma')
    ap.add_argument('--listar', action='store_true', help='solo enseñar las piezas')
    ap.add_argument('--listar-objetos', action='store_true',
                    help='enseñar cada objeto con su tamaño y su distancia al centro')
    a = ap.parse_args()

    bl = Blend(a.blend)
    if a.listar_objetos:
        listar_objetos(bl, a.giro_fino)
        return
    sin_ob = {x.strip() for x in a.sin_objetos.split(',') if x.strip()}
    V, grupos, colores = leer_escena(bl, a.soldadura, sin_ob)
    if not V:
        sys.exit('No he encontrado geometría de malla en el fichero.')

    for m in filter(None, a.fuera.split(',')):
        grupos.pop(m.strip(), None)

    # Compactar: al descartar materiales u objetos quedan vértices que ya no
    # usa ningún triángulo, y ocupan 12 bytes cada uno en el fichero.
    usados = {}
    for tris in grupos.values():
        for t in tris:
            for i in t:
                if i not in usados:
                    usados[i] = len(usados)
    if len(usados) < len(V):
        V = [V[i] for i in sorted(usados, key=usados.get)]
        for k, tris in grupos.items():
            grupos[k] = [(usados[a], usados[b], usados[c]) for a, b, c in tris]

    if a.listar:
        print(f'{len(V)} vértices soldados · {len(grupos)} materiales')
        for k in sorted(grupos, key=lambda k: -len(grupos[k])):
            c = colores.get(k, [0, 0, 0, 1])
            print(f'  {k:<26} {len(grupos[k]):>8} triángulos   rgb '
                  f'{c[0]:.2f} {c[1]:.2f} {c[2]:.2f}')
        return

    # Enderezar: muchos modelos vienen girados respecto a los ejes. El ángulo
    # se puede dar a mano o buscarlo: el que deja la caja en planta más pequeña
    # es el que alinea el óvalo con los ejes.
    import math
    giro = a.giro_fino
    if giro < 0:
        mejor = (1e30, 0)
        for gr in range(180):
            r = math.radians(gr); c1, s1 = math.cos(r), math.sin(r)
            xs = [p[0] * c1 + p[2] * s1 for p in V]
            zs = [-p[0] * s1 + p[2] * c1 for p in V]
            area = (max(xs) - min(xs)) * (max(zs) - min(zs))
            if area < mejor[0]:
                mejor = (area, gr)
        giro = mejor[1]
        print(f'giro automático: {giro}°')
    r = math.radians(giro); c1, s1 = math.cos(r), math.sin(r)
    V = [(p[0] * c1 + p[2] * s1, p[1], -p[0] * s1 + p[2] * c1) for p in V]

    # Normalizar: metros, suelo a cero, centrado y el lado largo sobre x.
    xs = [p[0] for p in V]; ys = [p[1] for p in V]; zs = [p[2] for p in V]
    cx, cz, suelo = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2, min(ys)
    V = [(p[0] - cx, p[1] - suelo, p[2] - cz) for p in V]

    s = a.escala
    if a.ajustar_hueco:
        # El hueco del cuenco: lo más cerca del eje que llega la primera fila.
        # Se mide en la franja de altura donde hay más geometría, que es el
        # graderío, y solo cerca del eje corto, para no coger las esquinas.
        alturas = sorted(p[1] for p in V)
        banda = alturas[int(len(alturas) * 0.3)], alturas[int(len(alturas) * 0.7)]
        cerca = [abs(p[0]) for p in V if banda[0] <= p[1] <= banda[1] and abs(p[2]) < 12]
        if cerca:
            hueco = min(cerca) * 2
            s = a.ajustar_hueco / hueco
            print(f'hueco interior medido: {hueco:.1f} unidades -> escala {s:.4f}')
    W = []
    co, si = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[a.giro]
    for x, y, z in V:
        x, y, z = x * s, y * s - a.baja, z * s
        W.append([x * co + z * si, y, -x * si + z * co])

    datos = glb(W, grupos, colores)
    open(a.salida, 'wb').write(datos)
    t = [round(max(p[i] for p in W) - min(p[i] for p in W), 2) for i in range(3)]
    tri = sum(len(v) for v in grupos.values())
    print(f'{a.salida}: {len(datos)/1024/1024:.2f} MB · {len(W)} vértices · {tri} triángulos'
          f' · {len(grupos)} materiales')
    print(f'tamaño final {t[0]} x {t[1]} x {t[2]} m')


if __name__ == '__main__':
    main()

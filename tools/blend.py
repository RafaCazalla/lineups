"""Lector mínimo de ficheros .blend, sin dependencias.

Un .blend es autodescriptivo: lleva dentro un bloque DNA1 con la definición de
todas sus estructuras, así que se puede leer sin Blender. Aquí solo se saca lo
que hace falta para llevar la geometría a la web: objetos con su matriz, mallas
con sus vértices y polígonos, materiales y UVs.

Probado con Blender 2.79 (punteros de 64 bits, little-endian).
"""
import struct


class Blend:
    def __init__(self, ruta):
        self.d = open(ruta, 'rb').read()
        cab = self.d[:12]
        if cab[:7] != b'BLENDER':
            raise ValueError('no parece un .blend (¿comprimido con gzip o zstd?)')
        self.p = 8 if cab[7:8] == b'-' else 4
        self.orden = '<' if cab[8:9] == b'v' else '>'
        self.bloques = []
        self.por_puntero = {}
        o = 12
        while o < len(self.d):
            code = self.d[o:o + 4].rstrip(b'\x00').decode('latin1')
            ln = struct.unpack(self.orden + 'I', self.d[o + 4:o + 8])[0]
            fmt = 'Q' if self.p == 8 else 'I'
            viejo = struct.unpack(self.orden + fmt, self.d[o + 8:o + 8 + self.p])[0]
            sdna, nr = struct.unpack(self.orden + 'II', self.d[o + 8 + self.p:o + 16 + self.p])
            b = dict(code=code, ini=o + 16 + self.p, len=ln, sdna=sdna, nr=nr)
            self.bloques.append(b)
            self.por_puntero[viejo] = b
            if code == 'ENDB':
                break
            o = b['ini'] + ln
        self._dna()

    # --- DNA ---------------------------------------------------------------
    def _dna(self):
        b = next(x for x in self.bloques if x['code'] == 'DNA1')
        d, o = self.d, b['ini'] + 4                      # saltar 'SDNA'

        def etiqueta(esperada):
            nonlocal o
            if d[o:o + 4] != esperada:
                raise ValueError(f'esperaba {esperada} y hay {d[o:o+4]}')
            o += 4

        def cuenta():
            nonlocal o
            n = struct.unpack(self.orden + 'I', d[o:o + 4])[0]
            o += 4
            return n

        def cadenas(n):
            nonlocal o
            fuera = []
            for _ in range(n):
                fin = d.index(b'\0', o)
                fuera.append(d[o:fin].decode('latin1'))
                o = fin + 1
            return fuera

        etiqueta(b'NAME'); self.nombres = cadenas(cuenta())
        o = (o + 3) & ~3
        etiqueta(b'TYPE'); self.tipos = cadenas(cuenta())
        o = (o + 3) & ~3
        # OJO: TLEN no lleva contador propio, usa el de TYPE. Leerlo como si lo
        # tuviera desplaza todo lo que viene detrás.
        etiqueta(b'TLEN')
        n = len(self.tipos)
        self.tlen = list(struct.unpack(self.orden + '%dH' % n, d[o:o + 2 * n]))
        o += 2 * n
        o = (o + 3) & ~3
        etiqueta(b'STRC')
        self.estructuras = []
        for _ in range(cuenta()):
            t, nc = struct.unpack(self.orden + 'HH', d[o:o + 4]); o += 4
            campos = []
            for _ in range(nc):
                ft, fn = struct.unpack(self.orden + 'HH', d[o:o + 4]); o += 4
                campos.append((ft, fn))
            self.estructuras.append((t, campos))
        self.por_nombre = {self.tipos[t]: i for i, (t, _) in enumerate(self.estructuras)}
        self._cache = {}

    def _tam(self, ti, nombre):
        base = self.p if nombre.startswith('*') else self.tlen[ti]
        n, rest = 1, nombre
        while '[' in rest:
            a, z = rest.index('['), rest.index(']')
            n *= int(rest[a + 1:z])
            rest = rest[z + 1:]
        return base * n

    def campos(self, idx):
        """{nombre: (desplazamiento, índice de tipo, nombre crudo)}"""
        if idx in self._cache:
            return self._cache[idx]
        fuera, off = {}, 0
        for ft, fn in self.estructuras[idx][1]:
            crudo = self.nombres[fn]
            fuera[crudo.lstrip('*').split('[')[0]] = (off, ft, crudo)
            off += self._tam(ft, crudo)
        self._cache[idx] = fuera
        return fuera

    # --- Lectura de valores ------------------------------------------------
    FMT = {'char': 'b', 'uchar': 'B', 'short': 'h', 'ushort': 'H', 'int': 'i',
           'long': 'i', 'ulong': 'I', 'float': 'f', 'double': 'd', 'int64_t': 'q',
           'uint64_t': 'Q'}

    def leer(self, base, campos, nombre, n=1):
        off, ti, crudo = campos[nombre]
        if crudo.startswith('*'):
            fmt = 'Q' if self.p == 8 else 'I'
            return struct.unpack_from(self.orden + fmt, self.d, base + off)[0]
        f = self.FMT.get(self.tipos[ti])
        if not f:
            return None
        v = struct.unpack_from(self.orden + '%d%s' % (n, f), self.d, base + off)
        return v[0] if n == 1 else list(v)

    def nombre_id(self, base):
        """El campo `id.name` empieza con dos letras de tipo: se quitan."""
        cru = self.d[base + 2 * self.p:base + 2 * self.p + 66].split(b'\0')[0]
        return cru.decode('latin1')[2:]

    def bloque_en(self, puntero):
        return self.por_puntero.get(puntero)

    def de_codigo(self, code):
        return [b for b in self.bloques if b['code'] == code]

#!/usr/bin/env python3
"""API de BeSoccer -> el bloque PARTIDO del prototipo. Sin dependencias.

    export BESOCCER_KEY=...
    python3 tools/besoccer_datos.py 208696 --year 2027 -o data/partido.json --inline index.html

La clave NUNCA se escribe en el repositorio ni en el HTML: se lee del entorno o
de --key, y solo se incrusta el resultado. Un prototipo desplegado en Vercel es
público, y una clave en el HTML es una clave regalada.

Peticiones:
  match_lineups       los 22 titulares con dorsal, rol, nota, foto y cambios
  match_events_stats  marcador, minuto, goles, tarjetas, cambios y estadísticas
  playerStats         una por jugador: estadísticas del partido, mapa de calor
                      y tiros con xG. Son 22 peticiones; --sin-stats las salta.

Y, aparte de la API, --pases admite un passMatrix de Opta (XML) con la matriz de
pases del partido. Se une por (equipo, dorsal), que es lo único común entre las
dos fuentes: los identificadores de jugador no se parecen en nada.

Lo que la API NO da:
  · la casilla de cada jugador en la táctica. Manda el nombre («4-2-3-1») y un
    `pos` de 1 a 11, y con eso se reparte la forma del equipo (ver posiciones()).
    BeSoccer ya advierte de que la alineación es automática. Para la posición
    REAL se usa el centroide del mapa de calor, que sí es dato medido.
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import date

BASE = 'https://fast.besoccer.com/scripts/api/api.php'
CDN_ESCUDO = 'https://cdn.resfu.com/img_data/equipos/{}.png?size=120x&lossy=1'

# Los colores de equipación no vienen en la API. Se ponen a mano por id de
# equipo; lo que no esté en la tabla sale en gris neutro, no en un color falso.
EQUIPACIONES = {
    '2107': {'fondo': '#F4F6F8', 'tinta': '#1B2B4B', 'borde': '#C9CDD6'},  # Real Madrid
    '1381': {'fondo': '#1C2E6B', 'tinta': '#FFFFFF', 'borde': '#48588F'},  # Inter
}
NEUTRA = {'fondo': '#ECECEC', 'tinta': '#383838', 'borde': '#A7A7A7'}
# Color de serie de cada lado, para las líneas de pase y la línea de tiempo.
# Sale de la paleta validada del panel, no de la camiseta: tiene que
# distinguirse sobre césped y bajo daltonismo.
ACENTOS = {'local': '#0A86C9', 'visitante': '#1A2340'}

ROL_LARGO = {'PT': 'Portero', 'DEF': 'Defensa', 'MED': 'Centrocampista', 'DEL': 'Delantero'}
# El rol que devuelve playerStats es más fino que el de las alineaciones.
ROL_FINO = {
    'PT': 'Portero', 'DFC': 'Central', 'LTD': 'Lateral derecho', 'LTI': 'Lateral izquierdo',
    'LD': 'Lateral derecho', 'LI': 'Lateral izquierdo', 'CD': 'Central derecho', 'CI': 'Central izquierdo',
    'CAD': 'Carrilero derecho', 'CAI': 'Carrilero izquierdo', 'MCD': 'Mediocentro defensivo',
    'CEN': 'Mediocentro', 'MC': 'Mediocentro', 'MP': 'Mediapunta', 'MD': 'Interior derecho',
    'MI': 'Interior izquierdo', 'ED': 'Extremo derecho', 'EI': 'Extremo izquierdo',
    'DC': 'Delantero centro', 'SD': 'Segundo delantero',
}


def pide(req, key, **params):
    q = {'req': req, 'site': 'ResultadosAndroid', 'isocode': 'es', 'lang': 'es',
         'format': 'json', 'key': key, **params}
    url = BASE + '?' + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=30) as r:
        crudo = r.read().decode('utf-8', 'replace')
    # La API cuela avisos de PHP delante del JSON en algunas respuestas.
    i = crudo.find('{')
    if i < 0:
        sys.exit(f'{req}: la respuesta no trae JSON\n{crudo[:200]}')
    return json.loads(crudo[i:])


def posiciones(tactica, n_por_linea, espejo):
    """Coordenadas normalizadas de los 11, en el orden en que la API los da.

    La API no manda x/y: manda el nombre de la táctica («4-2-3-1») y un `pos`
    de 1 a 11 que recorre las líneas de atrás hacia delante. Con eso se
    reparten: la profundidad por línea, y el ancho a partes iguales dentro de
    cada línea. `mirror_*_tactic` invierte el orden dentro de la línea.

    No es la posición real de cada jugador —eso no lo da la API, y BeSoccer ya
    avisa de que la alineación es automática—: es la forma del equipo.
    """
    fondo, frente = 0.045, 0.47
    lineas = len(n_por_linea)
    fuera = []
    for li, n in enumerate(n_por_linea):
        # Línea 0 = portero, pegado al fondo. El resto se reparte hasta el frente.
        if li == 0:
            x = fondo
        else:
            x = 0.15 + (li - 1) * (frente - 0.15) / max(1, lineas - 2)
        idx = range(n - 1, -1, -1) if espejo else range(n)
        for k in idx:
            fuera.append((x, 0.10 + (k + 0.5) / n * 0.80))
    return fuera


def filas_seccion(valores, filas, grupo=0):
    """Aplana las filas de una sección. Los `group` de la API solo marcan qué
    filas van juntas (goles con xG, asistencias con xA), así que se conserva el
    número de grupo para poder separarlas al pintar."""
    for v in valores:
        if v.get('type') == 'group':
            grupo += 1
            grupo = filas_seccion(v['values'], filas, grupo)
        elif v.get('type') == 'row':
            filas.append({'titulo': v.get('title'), 'valor': v.get('value'),
                          'color': v.get('lightColor'), 'grupo': grupo})
    return grupo


_FICHAS = {}


def ficha_jugador(pid, key):
    """Altura y peso. No vienen ni en las alineaciones ni en `playerStats`:
    hacen falta de `req=player`, una petición más por jugador. Se cachea por
    id porque un suplente puede pedirse dos veces."""
    if pid in _FICHAS:
        return _FICHAS[pid]
    try:
        d = pide('player', key, vr='1', id=pid) or {}
    except Exception as e:
        print(f'  ! player {pid}: {e}', file=sys.stderr)
        d = {}
    p = d.get('player') if isinstance(d.get('player'), dict) else d

    def num(v):
        try:
            return int(float(v)) or None
        except (TypeError, ValueError):
            return None

    _FICHAS[pid] = {'alto': num(p.get('height')), 'peso': num(p.get('weight'))}
    return _FICHAS[pid]


def stats_jugador(pid, match, year, key):
    """playerStats de un jugador: secciones, nota desglosada, mapa de calor y
    tiros. Devuelve None si la API no trae nada para ese jugador."""
    try:
        d = pide('playerStats', key, vr='1', matchId=match, year=year, id=pid)
    except Exception as e:
        print(f'  ! {pid}: {e}', file=sys.stderr)
        return None
    jug = d.get('player') or {}
    if not jug.get('teamId'):
        return None

    secciones = []
    for sec in (d.get('stats') or []):
        filas = []
        filas_seccion(sec.get('values') or [], filas)
        if filas:
            secciones.append({'nombre': sec.get('name'), 'clave': sec.get('key'),
                              'nota': sec.get('rating'), 'notaColor': sec.get('ratingLightColor'),
                              'filas': filas})

    r = d.get('rating') or {}
    mods = {m.get('key'): m.get('rating') for m in ((r.get('info') or {}).get('modules') or [])}
    fs = d.get('fieldStats') or {}
    calor = [[v['x'], v['y']] for v in ((fs.get('heatmap') or {}).get('values') or [])]
    tiros = [{'min': t.get('minute'), 'tipo': t.get('type'), 'titulo': t.get('title'),
              'pie': t.get('subtitle'),
              'x': (t.get('origin') or {}).get('x'), 'y': (t.get('origin') or {}).get('y'),
              'xg': next((s.get('value') for s in (t.get('stats') or []) if s.get('key') == 'xg'), None)}
             for t in ((fs.get('shots') or {}).get('values') or [])]

    fuera = {
        'rolApi': jug.get('role'), 'mvp': bool(jug.get('isMvp')),
        'notaValor': r.get('value'), 'notaColor': r.get('lightColor'),
        'bonos': mods.get('bonuses'), 'penalizaciones': mods.get('maluses'),
        'secciones': secciones, 'calor': calor, 'tiros': tiros,
    }
    if calor:
        # Posición media REAL: el centroide de los toques. Esto sí es medido,
        # a diferencia de la casilla deducida del nombre de la táctica.
        fuera['posMedia'] = [round(sum(c[0] for c in calor) / len(calor), 4),
                             round(sum(c[1] for c in calor) / len(calor), 4)]
    return fuera


def equipo(lado, lu, ev, goles):
    L = lu['lineups']
    clave = 'local' if lado == 'local' else 'visitor'
    tid = next((t for t, o in lu['team_names'].items() if o['side'] == clave), None)
    nombre = lu['team_names'][tid]['langs'].get('es') if tid else clave
    tactica = L.get(f'{clave}_tactic_name') or ''
    kit = EQUIPACIONES.get(tid, NEUTRA)
    return {
        'id': tid, 'nombre': nombre,
        'sigla': re.sub(r'[^A-ZÁÉÍÓÚÑ]', '', nombre.upper())[:3] or nombre[:3].upper(),
        'escudo': CDN_ESCUDO.format(tid) if tid else None,
        'goles': goles, 'entrenador': L.get(f'{clave}_coach'),
        'tactica': tactica, 'nota': L.get(f'{clave}_rating'),
        'edadMedia': L.get(f'{clave}_age'),
        'acento': ACENTOS[lado], **kit,
    }


def suplentes(lu, match=None, year=None, key=None):
    """El banquillo: los once de cada equipo, con el minuto en el que entraron.

    A los que ENTRARON se les piden `playerStats` y su altura y peso, igual que
    a un titular: han jugado, así que tienen ficha que enseñar. A los que se
    quedaron sentados no se les pide nada —no hay nada que pedir— y en la
    interfaz no se abren.
    """
    banco = lu.get('bench') or {}
    fuera = []
    for lado, clave in (('local', 'local'), ('visitante', 'visitor')):
        for p in banco.get(clave) or []:
            entra = int(p['in']) if str(p.get('in') or 0) != '0' else None
            # Quien entra en el 90 puede no tener nota: la API manda un «-».
            try:
                nota = float(p['rating']) if entra else None
            except (TypeError, ValueError):
                nota = None
            extra = {}
            if entra and key:
                print(f"  playerStats (suplente) {p['nick']}…")
                extra = stats_jugador(p['idplayer'], match, year, key) or {}
                extra.pop('posMedia', None)
                extra.update(ficha_jugador(p['idplayer'], key))
            fuera.append({
                'id': 's' + lado[0] + p['num'], 'idApi': p['idplayer'],
                'dorsal': int(p['num']), 'corto': p['nick'],
                'nombre': ' '.join(x for x in (p.get('name'), p.get('last_name')) if x).strip(),
                'rol': p['roleAbbr'], 'rolLargo': ROL_LARGO.get(p['roleAbbr'], p['roleAbbr']),
                'equipo': lado, 'foto': p.get('image'), 'edad': p.get('age'),
                # La nota solo tiene sentido si ha jugado; a quien no entró la
                # API le pone una igualmente y no significa nada.
                'nota': nota,
                'notaColor': (p.get('ratingColor') or {}).get('lightColor') if nota else None,
                'entra': entra,
                'goles': int(p.get('goals') or 0),
                'tarjetas': [{'tipo': c['action'], 'min': int(c['minute'])} for c in (p.get('cards') or [])],
                'rolLargoFino': ROL_FINO.get(extra.get('rolApi')) or ROL_LARGO.get(p['roleAbbr']),
                **extra,
            })
    return fuera


def jugadores(lu, match=None, year=None, key=None):
    L, fuera = lu['lineups'], []
    for lado, clave in (('local', 'local'), ('visitante', 'visitor')):
        once = L[clave]
        tactica = L.get(f'{clave}_tactic_name') or ''
        lineas = [1] + [int(x) for x in re.findall(r'\d+', tactica)]
        if sum(lineas) != len(once):
            # Sin táctica utilizable, se reparte por rol: portero, defensas,
            # centrocampistas, delanteros. Sale una forma coherente igual.
            orden = {'PT': 0, 'DEF': 1, 'MED': 2, 'DEL': 3}
            cuenta = [0, 0, 0, 0]
            for p in once:
                cuenta[orden.get(p['roleAbbr'], 2)] += 1
            lineas = [n for n in cuenta if n]
        espejo = bool(L.get(f'mirror_{clave}_tactic'))
        coords = posiciones(tactica, lineas, espejo)
        # `pos` recorre las líneas de atrás hacia delante.
        for p, (x, y) in zip(sorted(once, key=lambda q: int(q['pos'])), coords):
            extra = {}
            if key:
                print(f"  playerStats {p['nick']}…")
                extra = stats_jugador(p['idplayer'], match, year, key) or {}
            pm = extra.pop('posMedia', None)
            if key:
                extra.update(ficha_jugador(p['idplayer'], key))
            fuera.append({
                'id': lado[0] + p['num'], 'idApi': p['idplayer'],
                'dorsal': int(p['num']), 'corto': p['nick'],
                'nombre': ' '.join(x for x in (p.get('name'), p.get('last_name')) if x).strip(),
                'rol': p['roleAbbr'], 'rolLargo': ROL_LARGO.get(p['roleAbbr'], p['roleAbbr']),
                'equipo': lado,
                # El visitante ataca hacia el otro lado: se espeja la x.
                'x': round(x if lado == 'local' else 1 - x, 4),
                'y': round(y, 4),
                'nota': float(p['rating']) if p.get('rating') else None,
                'notaColor': (p.get('ratingColor') or {}).get('lightColor'),
                'foto': p.get('image'), 'edad': p.get('age'),
                'goles': int(p.get('goals') or 0),
                'tarjetas': [{'tipo': c['action'], 'min': int(c['minute'])} for c in (p.get('cards') or [])],
                'sale': int(p['out']) if str(p.get('out') or 0) != '0' else None,
                'capitan': bool(p.get('captain')),
                # Posición media medida. El eje x va de la portería propia a la
                # contraria, así que el visitante se espeja en los dos ejes:
                # su izquierda es nuestra derecha.
                'xMedia': None if not pm else round(pm[0] if lado == 'local' else 1 - pm[0], 4),
                'yMedia': None if not pm else round(pm[1] if lado == 'local' else 1 - pm[1], 4),
                'rolLargoFino': ROL_FINO.get(extra.get('rolApi')) or ROL_LARGO.get(p['roleAbbr']),
                **extra,
            })
    return fuera


TIPO_ACCION = {'1': 'gol', '2': 'gol', '3': 'penalti', '5': 'amarilla', '6': 'roja',
               '7': 'roja', '19': 'cambio', '21': 'poste'}


def eventos(ev):
    fuera = []
    for grupo in ('goals', 'cards', 'changes', 'occasions'):
        for e in (ev['events'].get(grupo) or []):
            extra = e.get('extra_player') or {}
            fuera.append({
                'min': int(e['minute']), 'tipo': TIPO_ACCION.get(e['action_type'], e['action_type']),
                'nombreAccion': e['action_name'],
                'equipo': 'local' if e.get('team') == 'local' else 'visitante',
                'jugador': e.get('player'), 'extra': extra.get('name'),
                'extraTipo': extra.get('type'), 'periodo': int(e.get('period') or 1),
            })
    return sorted(fuera, key=lambda e: (e['min'], e['tipo']))


def estadisticas(ev):
    fuera = []
    for filas in (ev.get('stats') or {}).get('stats', {}).values():
        for f in filas:
            v = (f.get('tabs_values') or {}).get('1') or {}
            t = f.get('typeItem')
            if t == 1:                                    # porcentaje puro
                fuera.append({'titulo': f['title'], 'local': v.get('local_percent'),
                              'visitante': v.get('visitor_percent'), 'sufijo': '%'})
            elif t == 2:                                  # tiros: total y a puerta
                fuera.append({'titulo': f['title'], 'local': v.get('total_local'),
                              'visitante': v.get('total_visitor'), 'sufijo': ''})
                fuera.append({'titulo': v.get('short_on_target_title') or 'A puerta',
                              'local': v.get('local_shots_on_target'),
                              'visitante': v.get('visitor_shots_on_target'), 'sufijo': ''})
            else:
                fuera.append({'titulo': f['title'], 'local': v.get('local'),
                              'visitante': v.get('visitor'), 'sufijo': ''})
    return [f for f in fuera if f['local'] is not None or f['visitante'] is not None]


def matriz_pases(ruta, jugadores):
    """passMatrix de Opta -> pases entre los titulares, en las claves de aquí.

    La unión con los datos de BeSoccer se hace por (equipo, dorsal): los ids de
    jugador de las dos fuentes no tienen nada que ver. Los pases con suplentes
    se descartan, porque los suplentes no están en el campo del prototipo."""
    crudo = open(ruta, encoding='utf-8').read()
    raiz = ET.fromstring(crudo[crudo.index('<passMatrix'):])
    alineaciones = raiz.findall('.//lineUp')
    if len(alineaciones) != 2:
        sys.exit(f'{ruta}: esperaba dos alineaciones y hay {len(alineaciones)}')

    porId = {}          # id de jugador de Opta -> id de aquí
    sueltos = 0
    # El primer lineUp es el local: el XML respeta el orden de contestants.
    for lado, lu in zip(('local', 'visitante'), alineaciones):
        porDorsal = {j['dorsal']: j for j in jugadores if j['equipo'] == lado}
        for p in lu.findall('player'):
            j = porDorsal.get(int(p.get('shirtNumber')))
            if j:
                porId[p.get('playerId')] = j['id']

    for lado, lu in zip(('local', 'visitante'), alineaciones):
        porDorsal = {j['dorsal']: j for j in jugadores if j['equipo'] == lado}
        for p in lu.findall('player'):
            j = porDorsal.get(int(p.get('shirtNumber')))
            if not j:
                continue
            j['pasesA'] = []
            for pp in p.findall('playerPass'):
                destino = porId.get(pp.get('playerId'))
                n = int((pp.text or '0').strip() or 0)
                if destino and n:
                    j['pasesA'].append([destino, n])
                elif n:
                    sueltos += n
            j['pasesA'].sort(key=lambda x: -x[1])
    return sueltos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('match', help='id del partido, p. ej. 208696')
    ap.add_argument('--year', default='2027')
    ap.add_argument('--key', default=os.environ.get('BESOCCER_KEY'))
    ap.add_argument('-o', '--salida', help='dónde escribir el JSON legible')
    ap.add_argument('--inline', help='index.html en el que sustituir el bloque PARTIDO')
    ap.add_argument('--sin-stats', action='store_true',
                    help='no pedir playerStats (22 peticiones menos, ficha sin estadísticas)')
    ap.add_argument('--pases', help='passMatrix de Opta (XML) con la matriz de pases')
    a = ap.parse_args()
    if not a.key:
        sys.exit('Falta la clave: BESOCCER_KEY en el entorno, o --key.')

    lu = pide('match_lineups', a.key, vr='4', year=a.year, match=a.match)
    ev = pide('match_events_stats', a.key, vr='8', year=a.year, id=a.match)
    if not (lu.get('lineups') or {}).get('local'):
        sys.exit(f'El partido {a.match} no trae alineaciones.')

    g = ev['events'].get('goals') or []
    gl = sum(1 for x in g if x.get('team') == 'local')
    gv = len(g) - gl
    t = ev.get('time') or {}
    minuto, anadido = int(t.get('minute') or 0), int(t.get('extra') or 0)

    partido = {
        'id': a.match,
        'fuente': 'API de BeSoccer · match_lineups + match_events_stats',
        'capturado': date.today().isoformat(),
        'avisoAlineacion': lu.get('lineupsAutoText'),
        'minuto': minuto, 'anadido': anadido,
        'estado': 'final' if minuto >= 90 else 'directo',
        'duracion': 90,
        'local': equipo('local', lu, ev, gl),
        'visitante': equipo('visitante', lu, ev, gv),
        'eventos': eventos(ev),
        'estadisticas': estadisticas(ev),
        'jugadores': jugadores(lu, a.match, a.year, None if a.sin_stats else a.key),
        'suplentes': suplentes(lu, a.match, a.year, None if a.sin_stats else a.key),
    }
    if a.pases:
        sueltos = matriz_pases(a.pases, partido['jugadores'])
        partido['fuentePases'] = f'Matriz de pases de Opta · {os.path.basename(a.pases)}'
        con = sum(1 for j in partido['jugadores'] if j.get('pasesA'))
        total = sum(n for j in partido['jugadores'] for _, n in (j.get('pasesA') or []))
        print(f'matriz de pases: {con}/22 jugadores · {total} pases entre titulares'
              f' · {sueltos} descartados por ser con suplentes')

    # La explicación de la nota es la misma para todos: se guarda una vez.
    partido['notaLeyenda'] = ('La valoración se calcula con un modelo de ponderación de '
                              'eventos: cada acción suma o resta según su impacto. En verde, '
                              'las que suman; en rojo, las que restan.')

    crudo = json.dumps(partido, ensure_ascii=False, indent=1)
    if a.salida:
        open(a.salida, 'w', encoding='utf-8').write(crudo + '\n')
        print(f'escrito {a.salida}')

    if a.inline:
        html = open(a.inline, encoding='utf-8').read()
        # Escapar «<» como <: un nombre con «</script» tumbaría la página.
        js = json.dumps(partido, ensure_ascii=False, indent=1).replace('<', '\\u003c')
        nuevo = f'/* PARTIDO:inicio */\nconst PARTIDO = {js};\n/* PARTIDO:fin */'
        html2, n = re.subn(r'/\* PARTIDO:inicio \*/.*?/\* PARTIDO:fin \*/', lambda m: nuevo, html, flags=re.S)
        if not n:
            sys.exit('No encuentro los marcadores /* PARTIDO:inicio */ … /* PARTIDO:fin */')
        open(a.inline, 'w', encoding='utf-8').write(html2)
        print(f'incrustado en {a.inline}')

    print(f"\n{partido['local']['nombre']} {gl} - {gv} {partido['visitante']['nombre']}"
          f"  ({minuto}+{anadido}', {partido['estado']})")
    print(f"tácticas: {partido['local']['tactica']} vs {partido['visitante']['tactica']}"
          f" · {len(partido['jugadores'])} jugadores"
          f" · {len(partido['eventos'])} sucesos · {len(partido['estadisticas'])} estadísticas")
    con_stats = sum(1 for j in partido['jugadores'] if j.get('secciones'))
    con_calor = sum(1 for j in partido['jugadores'] if j.get('calor'))
    tiros = sum(len(j.get('tiros') or []) for j in partido['jugadores'])
    print(f'por jugador: {con_stats}/22 con estadísticas · {con_calor}/22 con mapa de calor'
          f' · {tiros} tiros')
    sup = partido['suplentes']
    jugaron = [x for x in sup if x['entra']]
    print(f"banquillo: {len(sup)} suplentes · {len(jugaron)} entraron"
          f" · {sum(1 for x in jugaron if x.get('secciones'))} con estadísticas")
    sin_medidas = [j['corto'] for j in partido['jugadores'] if not j.get('alto')]
    if sin_medidas:
        print(f"sin altura: {', '.join(sin_medidas)}")


if __name__ == '__main__':
    main()

# us2se_converter.py — Universe Sandbox 2 → Space Engine Converter
# v3.3 — Сортировка тел по удалению от родителя (как в SE)

import zipfile
import json
import math
import os
import sys

# ─── РЕАЛЬНЫЕ ОРБИТЫ из базы NASA/JPL (фолбэк когда симуляция разлетелась) ────
KNOWN_ORBITS = {
    'mercury':      ('Sun',     0.387098, 0.2056, 7.005,    87.969,   'Planet'),
    'venus':        ('Sun',     0.723332, 0.0068, 3.395,   224.701,   'Planet'),
    'earth':        ('Sun',     1.000000, 0.0167, 0.000,   365.250,   'Planet'),
    'mars':         ('Sun',     1.523679, 0.0934, 1.851,   686.971,   'Planet'),
    'ceres':        ('Sun',     2.765348, 0.0755, 10.593, 1681.630,   'Planet'),
    'vesta':        ('Sun',     2.361790, 0.0882, 7.142,  1325.750,   'Planet'),
    'pallas':       ('Sun',     2.771838, 0.2312, 34.832, 1685.960,   'Planet'),
    'jupiter':      ('Sun',     5.202887, 0.0489, 1.305,  4332.590,   'Planet'),
    'saturn':       ('Sun',     9.536676, 0.0565, 2.485,  10759.220,  'Planet'),
    'uranus':       ('Sun',    19.189176, 0.0463, 0.773,  30688.500,  'Planet'),
    'neptune':      ('Sun',    30.069922, 0.0100, 1.770,  60182.000,  'Planet'),
    'pluto':        ('Sun',    39.482117, 0.2488, 17.140, 90560.000,  'Planet'),
    'eris':         ('Sun',    67.668000, 0.4418, 44.040,203600.000,  'Planet'),
    'makemake':     ('Sun',    45.430000, 0.1559, 28.960,113183.000,  'Planet'),
    'haumea':       ('Sun',    43.218000, 0.1887, 28.190,103468.000,  'Planet'),
    'moon':         ('Earth',   0.00257,  0.0549, 5.145,    27.322,   'Moon'),
    'luna':         ('Earth',   0.00257,  0.0549, 5.145,    27.322,   'Moon'),
    'phobos':       ('Mars',   0.0000627, 0.0151, 1.075,     0.319,   'Moon'),
    'deimos':       ('Mars',   0.0001568, 0.0003, 1.793,     1.263,   'Moon'),
    'io':           ('Jupiter', 0.002819, 0.0041, 0.036,     1.769,   'Moon'),
    'europa':       ('Jupiter', 0.004486, 0.0094, 0.470,     3.551,   'Moon'),
    'ganymede':     ('Jupiter', 0.007155, 0.0013, 0.195,     7.155,   'Moon'),
    'callisto':     ('Jupiter', 0.012585, 0.0074, 0.281,    16.690,   'Moon'),
    'titan':        ('Saturn',  0.008168, 0.0288, 0.348,    15.945,   'Moon'),
    'triton':       ('Neptune', 0.002370, 0.0000, 157.000,   5.877,   'Moon'),
}

G         = 6.674e-11
M_TO_AU   = 1.0 / 1.495978707e11
KG_TO_MSUN = 1.0 / 1.989e30
M_TO_KM   = 1.0 / 1000.0
DEFAULT_OUTPUT = r"d:\US2SE_Bridge\se_catalog"

MIN_SMA_PLANET_AU   = 0.02
MIN_SMA_MOON_AU     = 0.0001
MAX_SMA_PLANET_AU   = 200.0
MAX_SMA_MOON_AU     = 0.5
FALLBACK_SMA_PLANET = 5.0
FALLBACK_SMA_MOON   = 0.002

JUNK_NAME_PREFIXES = ('ui_string:', 'фрагмент', 'fragment', 'debris')
MIN_RADIUS_KM     = 100
MIN_RADIUS_SSO_KM = 0.1
MAX_RADIUS_KM     = 200_000

def is_junk(entity):
    name = (entity.get('Name') or '').strip()
    name_low = name.lower()
    if any(name_low.startswith(p) for p in JUNK_NAME_PREFIXES): return True
    if not name: return True
    radius_km = entity.get('Radius', 0) * M_TO_KM
    cat = entity.get('Category', '').lower()
    min_r = MIN_RADIUS_SSO_KM if cat == 'sso' else MIN_RADIUS_KM
    if radius_km < min_r or radius_km > MAX_RADIUS_KM: return True
    return False

def sanitize_orbit(orbit, se_type):
    sma = orbit['SemiMajorAxis_AU']
    if se_type == 'Moon':
        if sma < MIN_SMA_MOON_AU or sma > MAX_SMA_MOON_AU:
            orbit = dict(orbit); orbit['SemiMajorAxis_AU'] = FALLBACK_SMA_MOON
    else:
        if sma < MIN_SMA_PLANET_AU:
            orbit = dict(orbit); orbit['SemiMajorAxis_AU'] = max(sma * 10, MIN_SMA_PLANET_AU)
        elif sma > MAX_SMA_PLANET_AU:
            orbit = dict(orbit); orbit['SemiMajorAxis_AU'] = FALLBACK_SMA_PLANET
    return orbit

def parse_vec3(s):
    try: return [float(p) for p in str(s).split(';')]
    except: return [0.0, 0.0, 0.0]

def vec_sub(a, b): return [a[i] - b[i] for i in range(3)]
def vec_len(v): return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)

def cross(a, b):
    return [a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]]

def compute_kepler_orbit(pos_rel_m, vel_rel_ms, parent_mass_kg):
    mu = G * parent_mass_kg
    r, v = vec_len(pos_rel_m), vec_len(vel_rel_ms)
    if r < 1e3 or mu < 1e5 or v < 0.001: return None
    denom = 2.0 / r - v * v / mu
    if denom <= 0: return None
    semi_major_m = 1.0 / denom
    h = cross(pos_rel_m, vel_rel_ms)
    h_len = vec_len(h)
    vxh = cross(vel_rel_ms, h)
    e_vec = [(vxh[i]/mu - pos_rel_m[i]/r) for i in range(3)]
    ecc = min(vec_len(e_vec), 0.9999)
    inc_deg = math.degrees(math.acos(max(-1.0, min(1.0, h[2] / h_len)))) if h_len > 0 else 0.0
    period_s = 2.0 * math.pi * math.sqrt(semi_major_m**3 / mu)
    return {
        'SemiMajorAxis_AU': semi_major_m * M_TO_AU, 'Eccentricity': ecc,
        'Inclination': inc_deg, 'Period_days': period_s / 86400.0, 'source': 'computed'
    }

def get_known_orbit(name):
    key = name.strip().lower()
    if key in KNOWN_ORBITS:
        p, sma, ecc, inc, period, se_type = KNOWN_ORBITS[key]
        return {'ParentOverride': p, 'SemiMajorAxis_AU': sma, 'Eccentricity': ecc, 
                'Inclination': inc, 'Period_days': period, 'SEType': se_type}
    return None

def find_nearest_parent(entity, all_entities, preferred_cats):
    pos, mass = parse_vec3(entity['Position']), entity.get('PhysicsMass', 0)
    best, best_dist = None, float('inf')
    for e in all_entities:
        if e['Id'] == entity['Id']: continue
        if e.get('Category', '').lower() not in preferred_cats: continue
        if e.get('PhysicsMass', 0) <= mass: continue
        d = vec_len(vec_sub(pos, parse_vec3(e['Position'])))
        if d < best_dist: best_dist, best = d, e
    return best, best_dist

def resolve_se_type(cat, parent, entities, center):
    if cat == 'moon':
        if parent is None or parent.get('Category', '').lower() == 'star': return 'Planet', center
        return 'Moon', parent
    elif cat == 'sso': return 'Asteroid', parent if parent else center
    return 'Planet', parent if parent else center

def resolve_se_class(entity):
    radius_km = entity.get('Radius', 0) * M_TO_KM
    cat_us2 = str(entity.get('Category', '')).lower()
    if 'giant' in cat_us2 or radius_km > 20000: return 'GasGiant'
    if radius_km < 1000: return 'Asteroid'
    return 'Terra'

def entity_to_sc(entity, parent, orbit_data, se_type, se_star_name):
    name = entity.get('Name') or 'Body_' + str(entity.get('Id', '?'))
    mass_kg, radius_m = entity.get('PhysicsMass', 0), entity.get('Radius', 1000)
    p_name = parent.get('Name', 'Sun')
    parent_name = se_star_name if (p_name.lower() == 'sun' or parent.get('Category', '').lower() == 'star') else p_name
    
    se_class = resolve_se_class(entity)
    temp_k, albedo = float(entity.get('SurfaceTemperature', 0)), float(entity.get('Albedo', 0.3))
    
    lines = [
        f'{se_type} "{name}"', '{', f'    ParentBody "{parent_name}"', f'    Class      "{se_class}"',
        f'    Mass       {mass_kg * KG_TO_MSUN:.10e}', f'    Radius     {radius_m*M_TO_KM:.4f}', f'    Albedo     {albedo:.3f}'
    ]
    if temp_k > 1.0: lines.append(f'    SurfaceTemp {temp_k:.1f}')

    # Атмосфера
    atm_mass = 0
    for comp in entity.get('Components', []):
        if comp.get('$type', '') == 'Celestial': atm_mass = comp.get('AtmosphereMass', 0)
    if atm_mass > 1e14:
        gravity = (G * mass_kg) / (radius_m**2)
        pressure_atm = ((atm_mass * gravity) / (4 * math.pi * radius_m**2)) / 101325.0
        lines.extend(['    Atmosphere', '    {', f'        Model    "Earth"', f'        Pressure {pressure_atm:.6f}', '    }'])

    lines.extend([f'    Orbit', '    {', f'        SemiMajorAxis {orbit_data["SemiMajorAxis_AU"]:.8f}',
                  f'        Eccentricity  {orbit_data["Eccentricity"]:.6f}',
                  f'        Inclination   {orbit_data["Inclination"]:.4f}',
                  f'        Period        {orbit_data["Period_days"]:.4f}', '    }', '}'])
    return '\n'.join(lines)

def find_ubox():
    # Поиск последней симуляции в папке Документы (fallback)
    docs = os.path.join(os.path.expanduser("~"), "Documents", "Universe Sandbox", "Simulations")
    if not os.path.isdir(docs): return None
    files = [os.path.join(docs, f) for f in os.listdir(docs) if f.endswith('.ubox')]
    if not files: return None
    return max(files, key=os.path.getmtime)

def convert(ubox_path=None, output_dir=DEFAULT_OUTPUT):
    if not ubox_path: ubox_path = find_ubox()
    if not ubox_path: print("Не удалось найти .ubox"); return
    
    with zipfile.ZipFile(ubox_path, 'r') as zf:
        with zf.open('simulation.json') as fp: data = json.load(fp)

    entities = data.get('Entities', [])
    stars = [e for e in entities if e.get('Category') == 'star']
    center = max(stars or entities, key=lambda e: e.get('PhysicsMass', 0))
    
    os.makedirs(output_dir, exist_ok=True)
    renderer = US2SE_Converter(None)
    sc_text = renderer._generate_sc_content(entities, center, os.path.basename(ubox_path), 'Sun')
    
    out_path = os.path.join(output_dir, 'catalog.sc')
    with open(out_path, 'w', encoding='utf-8') as f: f.write(sc_text)
    print(f"Готово: {out_path}")

class US2SE_Converter:
    def __init__(self, se_install_dir):
        self.se_install_dir = se_install_dir
        if se_install_dir: self.output_base = os.path.join(se_install_dir, 'addons', 'catalogs', 'planets')

    def convert_ubox(self, ubox_path, catalog_name='US2_IMPORT', se_star_name='Sun'):
        with zipfile.ZipFile(ubox_path, 'r') as zf:
            with zf.open('simulation.json') as fp: data = json.load(fp)
        entities = data.get('Entities', [])
        center = max([e for e in entities if e.get('Category')=='star'] or entities, key=lambda e: e.get('PhysicsMass',0))
        sc_text = self._generate_sc_content(entities, center, os.path.basename(ubox_path), se_star_name)
        
        os.makedirs(self.output_base, exist_ok=True)
        out_path = os.path.join(self.output_base, catalog_name + '.sc')
        with open(out_path, 'w', encoding='utf-8') as f: f.write(sc_text)
        return out_path

    def _generate_sc_content(self, entities, center, source_name, se_star_name):
        header = [f'// US2SE v3.3 - Sorted by Distance', f'// Source: {source_name}', '']
        processed, seen = [], set()
        for e in entities:
            if e['Id'] == center['Id'] or is_junk(e): continue
            name = (e.get('Name') or '').strip()
            if not name or any(x in name.lower() for x in ['camera', 'dummy']) or name.lower() in seen: continue
            seen.add(name.lower())
            
            cat = e.get('Category', '').lower()
            known = get_known_orbit(name)
            if known:
                p_db = next((obj for obj in entities if obj.get('Name','').lower()==known['ParentOverride'].lower()), None)
                parent = p_db if p_db else center
                orbit = {'SemiMajorAxis_AU': known['SemiMajorAxis_AU'], 'Eccentricity': known['Eccentricity'], 
                         'Inclination': known['Inclination'], 'Period_days': known['Period_days'], 'source': 'DB'}
                se_type = known['SEType']
            else:
                if cat == 'moon':
                    rp, _ = find_nearest_parent(e, entities, {'planet', 'star'})
                    se_type, parent = resolve_se_type(cat, rp, entities, center)
                elif cat == 'sso':
                    parent, _ = find_nearest_parent(e, entities, {'star', 'planet'})
                    se_type = 'Asteroid'
                else:
                    parent, _ = find_nearest_parent(e, entities, {'star'})
                    se_type = 'Planet'
                if not parent: parent = center
                pos, vel = vec_sub(parse_vec3(e['Position']), parse_vec3(parent['Position'])), vec_sub(parse_vec3(e['Velocity']), parse_vec3(parent['Velocity']))
                orbit = compute_kepler_orbit(pos, vel, parent.get('PhysicsMass', 1e30))
                if not orbit: orbit = {'SemiMajorAxis_AU': vec_len(pos)*M_TO_AU, 'Eccentricity': 0.0, 'Inclination': 0.0, 'Period_days': 1.0, 'source': 'fallback'}

            processed.append({'entity': e, 'parent_id': parent['Id'], 'orbit': sanitize_orbit(orbit, se_type), 'se_type': se_type})

        by_parent, final_lines = {}, []
        for b in processed:
            pid = b['parent_id']
            if pid not in by_parent: by_parent[pid] = []
            by_parent[pid].append(b)

        def _add_children(pid):
            children = sorted(by_parent.get(pid, []), key=lambda x: x['orbit']['SemiMajorAxis_AU'])
            for c in children:
                final_lines.append(entity_to_sc(c['entity'], next(e for e in entities if e['Id']==c['parent_id']), c['orbit'], c['se_type'], se_star_name))
                final_lines.append('')
                _add_children(c['entity']['Id'])

        _add_children(center['Id'])
        return '\n'.join(header + final_lines)

if __name__ == '__main__':
    convert(sys.argv[1] if len(sys.argv) > 1 else None)

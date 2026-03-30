# us2se_converter.py — Universe Sandbox 2 → Space Engine Converter
# v3.1 — Добавлен класс US2SE_Converter для совместимости с live_sync.py
# v3.0 — BUGFIX:
#   - SemiMajorAxis считается ОТНОСИТЕЛЬНО родителя (не от начала координат).
#   - Спутники (moon) привязываются к ближайшей планете (не к звезде).
#   - База данных NASA/JPL как фолбэк при гиперболических орбитах.

import zipfile
import json
import math
import os
import sys

# ─── РЕАЛЬНЫЕ ОРБИТЫ из базы NASA/JPL (фолбэк когда симуляция разлетелась) ────
# SemiMajorAxis в AU, относительно родителя
KNOWN_ORBITS = {
    # name_lower -> (parent_name, SMA_AU, ecc, inc_deg, period_days, se_type)
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
    # Спутники Земли
    'moon':         ('Earth',   0.00257,  0.0549, 5.145,    27.322,   'Moon'),
    'luna':         ('Earth',   0.00257,  0.0549, 5.145,    27.322,   'Moon'),
    # Спутники Марса
    'phobos':       ('Mars',   0.0000627, 0.0151, 1.075,     0.319,   'Moon'),
    'deimos':       ('Mars',   0.0001568, 0.0003, 1.793,     1.263,   'Moon'),
    # Спутники Юпитера
    'io':           ('Jupiter', 0.002819, 0.0041, 0.036,     1.769,   'Moon'),
    'europa':       ('Jupiter', 0.004486, 0.0094, 0.470,     3.551,   'Moon'),
    'ganymede':     ('Jupiter', 0.007155, 0.0013, 0.195,     7.155,   'Moon'),
    'callisto':     ('Jupiter', 0.012585, 0.0074, 0.281,    16.690,   'Moon'),
    'amalthea':     ('Jupiter', 0.001213, 0.0032, 0.380,     0.498,   'Moon'),
    'himalia':      ('Jupiter', 0.076000, 0.1620, 27.500,   250.600,  'Moon'),
    # Спутники Сатурна
    'titan':        ('Saturn',  0.008168, 0.0288, 0.348,    15.945,   'Moon'),
    'rhea':         ('Saturn',  0.003523, 0.0013, 0.327,     4.518,   'Moon'),
    'dione':        ('Saturn',  0.002523, 0.0022, 0.028,     2.737,   'Moon'),
    'tethys':       ('Saturn',  0.001971, 0.0001, 1.120,     1.888,   'Moon'),
    'enceladus':    ('Saturn',  0.001590, 0.0047, 0.009,     1.370,   'Moon'),
    'mimas':        ('Saturn',  0.001241, 0.0196, 1.574,     0.942,   'Moon'),
    'iapetus':      ('Saturn',  0.023813, 0.0286, 15.470,   79.322,   'Moon'),
    'hyperion':     ('Saturn',  0.009914, 0.1230, 0.615,    21.277,   'Moon'),
    # Спутники Урана
    'titania':      ('Uranus',  0.002917, 0.0011, 0.340,     8.706,   'Moon'),
    'oberon':       ('Uranus',  0.003906, 0.0014, 0.058,    13.463,   'Moon'),
    'umbriel':      ('Uranus',  0.001784, 0.0039, 0.128,     4.144,   'Moon'),
    'ariel':        ('Uranus',  0.001277, 0.0012, 0.041,     2.520,   'Moon'),
    'miranda':      ('Uranus',  0.000866, 0.0013, 4.338,     1.414,   'Moon'),
    # Спутники Нептуна
    'triton':       ('Neptune', 0.002370, 0.0000, 157.000,   5.877,   'Moon'),
    'nereid':       ('Neptune', 0.036868, 0.7507, 7.232,   360.140,   'Moon'),
    # Спутники Плутона
    'charon':       ('Pluto',   0.000107, 0.0002, 0.001,     6.387,   'Moon'),
    'nix':          ('Pluto',   0.000320, 0.0020, 0.133,    24.854,   'Moon'),
    'hydra':        ('Pluto',   0.000428, 0.0059, 0.242,    38.202,   'Moon'),
    # Спутники Эриды
    'dysnomia':     ('Eris',    0.000249, 0.0062, 61.000,   15.786,   'Moon'),
    # Кометы
    '1p/halley':    ('Sun',     17.834144, 0.9671, 162.260, 27511.0,  'Comet'),
    'halley':       ('Sun',     17.834144, 0.9671, 162.260, 27511.0,  'Comet'),
}
# ─────────────────────────────────────────────────────────────────────────────

G         = 6.674e-11
M_TO_AU   = 1.0 / 1.495978707e11
KG_TO_MSUN = 1.0 / 1.989e30
M_TO_KM   = 1.0 / 1000.0
DEFAULT_OUTPUT = r"d:\US2SE_Bridge\se_catalog"

# Санитайзер орбит: SMA в AU
MIN_SMA_PLANET_AU   = 0.02   # ≈ 3 млн км — минимум для планеты (не внутри звезды)
MIN_SMA_MOON_AU     = 0.0001 # ок для спутников газовых гигантов
MAX_SMA_PLANET_AU   = 200.0  # всё выше — выброс симуляции
MAX_SMA_MOON_AU     = 0.5    # спутник не может быть дальше 0.5 AU от планеты
FALLBACK_SMA_PLANET = 5.0    # AU — дефолт при выбросе
FALLBACK_SMA_MOON   = 0.002  # AU — дефолт при выбросе

# Фильтр мусора — имена которые надо пропускать (регистр не важен)
JUNK_NAME_PREFIXES = ('ui_string:', 'фрагмент', 'fragment', 'debris')
MIN_RADIUS_KM     = 100    # меньше — мусор для планет/лун
MIN_RADIUS_SSO_KM = 0.1   # астероиды могут быть маленькими
MAX_RADIUS_KM     = 200_000

def is_junk(entity):
    """True если объект — мусор/фрагмент."""
    name = (entity.get('Name') or '').strip()
    name_low = name.lower()
    if any(name_low.startswith(p) for p in JUNK_NAME_PREFIXES):
        return True
    if not name:
        return True
    radius_km = entity.get('Radius', 0) * M_TO_KM
    cat = entity.get('Category', '').lower()
    min_r = MIN_RADIUS_SSO_KM if cat == 'sso' else MIN_RADIUS_KM
    if radius_km < min_r or radius_km > MAX_RADIUS_KM:
        return True
    return False


def sanitize_orbit(orbit, se_type):
    """Проверяет и корректирует SMA орбиты чтобы избежать артефактов SE."""
    sma = orbit['SemiMajorAxis_AU']
    if se_type == 'Moon':
        if sma < MIN_SMA_MOON_AU or sma > MAX_SMA_MOON_AU:
            print(f"    [SANITIZE] Moon SMA={sma:.6f} AU → исправлено на {FALLBACK_SMA_MOON} AU")
            orbit = dict(orbit)
            orbit['SemiMajorAxis_AU'] = FALLBACK_SMA_MOON
            orbit['source'] = orbit.get('source','?') + ' [sanitized]'
    else:  # Planet, Asteroid, Comet
        if sma < MIN_SMA_PLANET_AU:
            # Объект внутри или вплотную к звезде — это вызывает артефакт «овала»
            corrected = max(sma * 10, MIN_SMA_PLANET_AU)
            print(f"    [SANITIZE] Planet SMA={sma:.6f} AU < {MIN_SMA_PLANET_AU} → исправлено на {corrected:.4f} AU (объект был внутри звезды!)")
            orbit = dict(orbit)
            orbit['SemiMajorAxis_AU'] = corrected
            orbit['source'] = orbit.get('source','?') + ' [sanitized: too_close]'
        elif sma > MAX_SMA_PLANET_AU:
            print(f"    [SANITIZE] Planet SMA={sma:.2f} AU > {MAX_SMA_PLANET_AU} → исправлено на {FALLBACK_SMA_PLANET} AU (выброс симуляции)")
            orbit = dict(orbit)
            orbit['SemiMajorAxis_AU'] = FALLBACK_SMA_PLANET
            orbit['source'] = orbit.get('source','?') + ' [sanitized: runaway]'
    return orbit


def parse_vec3(s):
    try:
        return [float(p) for p in str(s).split(';')]
    except:
        return [0.0, 0.0, 0.0]


def vec_sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def vec_len(v):
    return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)


def cross(a, b):
    return [
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0],
    ]


def compute_kepler_orbit(pos_rel_m, vel_rel_ms, parent_mass_kg):
    """
    Считает Кеплеровы элементы из относительной pos/vel.
    Возвращает dict или None если орбита гиперболическая/некорректная.
    """
    mu = G * parent_mass_kg
    r  = vec_len(pos_rel_m)
    v  = vec_len(vel_rel_ms)

    if r < 1e3 or mu < 1e5 or v < 0.001:
        return None

    denom = 2.0 / r - v * v / mu
    if denom <= 0:
        return None  # гиперболическая — невалидно

    semi_major_m = 1.0 / denom

    # Эксцентриситет
    h = cross(pos_rel_m, vel_rel_ms)
    h_len = vec_len(h)
    vxh = cross(vel_rel_ms, h)
    r_len = vec_len(pos_rel_m)
    e_vec = [(vxh[i]/mu - pos_rel_m[i]/r_len) for i in range(3)]
    ecc = min(vec_len(e_vec), 0.9999)

    # Наклонение
    inc_deg = math.degrees(math.acos(max(-1.0, min(1.0, h[2] / h_len)))) if h_len > 0 else 0.0

    # Период
    period_s = 2.0 * math.pi * math.sqrt(semi_major_m**3 / mu)
    period_d = period_s / 86400.0

    return {
        'SemiMajorAxis_AU': semi_major_m * M_TO_AU,
        'Eccentricity':     ecc,
        'Inclination':      inc_deg,
        'Period_days':      period_d,
        'source':           'computed',
    }


def get_known_orbit(name):
    """Возвращает орбитальные данные из встроенной базы, если известны."""
    key = name.strip().lower()
    if key in KNOWN_ORBITS:
        p, sma, ecc, inc, period, se_type = KNOWN_ORBITS[key]
        return {
            'ParentOverride':   p,
            'SemiMajorAxis_AU': sma,
            'Eccentricity':     ecc,
            'Inclination':      inc,
            'Period_days':      period,
            'SEType':           se_type,
            'source':           'database',
        }
    return None


def find_nearest_parent(entity, all_entities, preferred_cats):
    """Ищет ближайшее тело из preferred_cats, которое массивнее текущего."""
    pos  = parse_vec3(entity['Position'])
    mass = entity.get('PhysicsMass', 0)
    best, best_dist = None, float('inf')

    for e in all_entities:
        if e['Id'] == entity['Id']:
            continue
        if e.get('Category', '').lower() not in preferred_cats:
            continue
        if e.get('PhysicsMass', 0) <= mass:
            continue
        d = vec_len(vec_sub(pos, parse_vec3(e['Position'])))
        if d < best_dist:
            best_dist = d
            best = e

    return best, best_dist


def resolve_se_type(cat, parent, entities, center):
    """
    Определяет тип SE (‘Planet’/‘Moon’/‘Asteroid’) и родителя.
    Если объект помечен moon, но его ближайший массивный родитель — звезда,
    переклассифицируем в Planet (иначе SE его просто не покажет).
    """
    if cat == 'moon':
        if parent is None or parent.get('Category', '').lower() == 'star':
            # Орфан-спутник — поднять до планеты
            return 'Planet', center
        return 'Moon', parent
    elif cat == 'sso':
        return 'Asteroid', parent if parent else center
    else:
        return 'Planet', parent if parent else center


def resolve_se_class(entity):
    """Определяет Class для SE (GasGiant, Terra, и т.д.)"""
    radius_km = entity.get('Radius', 0) * M_TO_KM
    # Если в US2 это газовый гигант (>20к км или категория)
    cat_us2 = str(entity.get('Category', '')).lower()
    
    if 'gas giant' in cat_us2 or 'ice giant' in cat_us2 or radius_km > 20000:
        return 'GasGiant'
    if radius_km < 1000:
        return 'Asteroid'
    return 'Terra'  # По умолчанию для каменистых


def entity_to_sc(entity, parent, orbit_data, se_type='Planet', se_star_name='Sun'):
    """Генерирует блок .sc для Space Engine."""
    name      = entity.get('Name') or 'Body_' + str(entity.get('Id', '?'))
    mass_kg   = entity.get('PhysicsMass', 0)
    radius_m  = entity.get('Radius', 1000)
    radius_km = radius_m * M_TO_KM
    
    # Если родитель — звезда и её имя совпадает с центром "Sun", подставляем se_star_name
    p_name = parent.get('Name', 'Sun')
    if p_name.lower() == 'sun' or parent.get('Category', '').lower() == 'star':
        parent_name = se_star_name
    else:
        parent_name = p_name

    # Класс планеты (визуальное отображение)
    se_class = resolve_se_class(entity)

    # Климат из US2
    # Температура в US2 (Кельвины), в SE SurfaceTemp тоже в Кельвинах
    temp_k = float(entity.get('SurfaceTemperature', 0))
    # Если температура не задана — SE сам посчитает по светимости звезды
    
    # Отражающая способность (0.3 — стандарт для Земли)
    albedo = float(entity.get('Albedo', 0.3))

    sma    = orbit_data['SemiMajorAxis_AU']
    ecc    = orbit_data['Eccentricity']
    inc    = orbit_data['Inclination']
    period = orbit_data['Period_days']
    src    = orbit_data.get('source', '?')

    # --- ИЗВЛЕЧЕНИЕ АТМОСФЕРЫ И ОБЛАКОВ ---
    atm_mass = 0
    atm_color = None
    cloud_opacity = 0
    cloud_coverage = 0
    
    components = entity.get('Components', [])
    for comp in components:
        ctype = comp.get('$type', '')
        if ctype == 'Celestial':
            atm_mass = comp.get('AtmosphereMass', 0)
        elif ctype == 'AppearanceComponent':
            p_data = comp.get('Planet', {})
            if p_data.get('ShowAtmosphere'):
                c_str = p_data.get('AtmosphereColor', 'RGBA(0.5, 0.5, 0.5, 1.0)')
                # RGBA(0.212, 0.325, 0.510, 1.000) -> [0.212, 0.325, 0.510]
                try:
                    atm_color = c_str.split('(')[1].split(')')[0].split(',')[:3]
                    atm_color = " ".join([c.strip() for c in atm_color])
                except:
                    atm_color = "0.5 0.6 1.0"
            
            if p_data.get('ShowAtmosphereClouds'):
                cloud_opacity = p_data.get('CloudOpacity', 0)
                cloud_coverage = p_data.get('CloudCoverage', 0)

    lines = [
        f'{se_type} "{name}"',
        '{',
        f'    ParentBody "{parent_name}"',
        f'    Class      "{se_class}"',
        f'    Mass       {mass_kg * KG_TO_MSUN:.10e}',
        f'    Radius     {radius_km:.4f}',
        f'    Albedo     {albedo:.3f}',
    ]
    
    # Добавляем температуру только если она выше 0
    if temp_k > 1.0:
        lines.append(f'    SurfaceTemp {temp_k:.1f}')

    # Добавляем Атмосферу (если есть масса)
    if atm_mass > 1e14: # Минимум для заметности
        # Примерный расчет давления: P = (M_atm * g) / Area
        gravity = (G * mass_kg) / (radius_m**2)
        area = 4 * math.pi * (radius_m**2)
        pressure_pa = (atm_mass * gravity) / area
        pressure_atm = pressure_pa / 101325.0
        
        lines.append('    Atmosphere')
        lines.append('    {')
        lines.append(f'        Model       "Earth"') # Дефолтная модель для каменистых
        lines.append(f'        Pressure    {pressure_atm:.6f}')
        if atm_color:
            lines.append(f'        Color       ({atm_color})')
        lines.append('    }')

    # Добавляем Облака
    if cloud_opacity > 0.05 and cloud_coverage > 0.05:
        lines.append('    Clouds')
        lines.append('    {')
        lines.append(f'        Coverage    {cloud_coverage:.2f}')
        lines.append(f'        Height      10') # Средняя высота
        lines.append(f'        Color       (1.0 1.0 1.0 {cloud_opacity:.2f})')
        lines.append('    }')
        
    lines.extend([
        f'    // orbit source: {src}',
        '    Orbit',
        '    {',
        f'        SemiMajorAxis {sma:.8f}',
        f'        Eccentricity  {ecc:.6f}',
        f'        Inclination   {inc:.4f}',
        f'        Period        {period:.4f}',
        '    }',
        '}',
    ])
    return '\n'.join(lines)


def find_ubox():
    sim_dir = r"D:\Universe Sandbox\Simulations"
    files = [f for f in os.listdir(sim_dir) if f.endswith('.ubox') and os.path.isfile(os.path.join(sim_dir, f))]
    if not files:
        raise FileNotFoundError("Нет .ubox файлов")
    files.sort(key=lambda f: os.path.getmtime(os.path.join(sim_dir, f)), reverse=True)
    return os.path.join(sim_dir, files[0])


def convert(ubox_path=None, output_dir=DEFAULT_OUTPUT):
    if not ubox_path:
        ubox_path = find_ubox()
    print(f"Читаем: {ubox_path}")

    with zipfile.ZipFile(ubox_path, 'r') as zf:
        with zf.open('simulation.json') as fp:
            data = json.load(fp)

    entities  = data.get('Entities', [])
    id_map    = {e['Id']: e for e in entities}
    print(f"Объектов: {len(entities)}")

    # Центр — активная звезда (самая массивная)
    stars  = [e for e in entities if e.get('Category') == 'star']
    center = max(stars or entities, key=lambda e: e.get('PhysicsMass', 0))
    print(f"Центр: {center['Name']}")

    os.makedirs(output_dir, exist_ok=True)

    header = [
        '// Сгенерировано us2se_converter.py v3.2',
        f'// Источник: {os.path.basename(ubox_path)}',
        f'// Центр: {center["Name"]}',
        '',
    ]
    planet_lines = []  # сначала звёзды и планеты
    moon_lines   = []  # потом луны (чтобы родитель уже был в файле)
    seen_names   = set()  # защита от дубль с одинаковым именем

    def _process_entity(entity):
        nonlocal seen_names
        name = entity.get('Name', '')
        cat  = entity.get('Category', '').lower()
        if not name or 'camera' in name.lower() or 'dummy' in name.lower():
            return
        if entity['Id'] == center['Id']:
            return
        if is_junk(entity):
            print(f"  [SKIP]     {name[:40]:40s} (мусор/фрагмент)")
            return
        name_key = name.strip().lower()
        if name_key in seen_names:
            print(f"  [DUP]      {name[:40]:40s} (дубликат — пропущен)")
            return
        seen_names.add(name_key)

        known = get_known_orbit(name)
        if known:
            parent_name_db = known['ParentOverride']
            parent_from_db = next(
                (e for e in entities if e.get('Name', '').strip().lower() == parent_name_db.lower()),
                None
            )
            if parent_from_db is None:
                if cat == 'moon':
                    parent_from_db, _ = find_nearest_parent(entity, entities, {'planet', 'star'})
                parent = parent_from_db if parent_from_db else center
            else:
                parent = parent_from_db
            orbit = {
                'SemiMajorAxis_AU': known['SemiMajorAxis_AU'],
                'Eccentricity':     known['Eccentricity'],
                'Inclination':      known['Inclination'],
                'Period_days':      known['Period_days'],
                'source':           'NASA/JPL database',
            }
            se_type = known['SEType']
            method  = 'DB'
        else:
            if cat == 'moon':
                # Луны: ищем ближайшую планету ИЛИ звезду, потом проверяем
                raw_parent, _ = find_nearest_parent(entity, entities, {'planet', 'star'})
                se_type, parent = resolve_se_type(cat, raw_parent, entities, center)
            elif cat == 'sso':
                parent, _ = find_nearest_parent(entity, entities, {'star'})
                se_type = 'Asteroid'
                if parent is None:
                    parent = center
            else:
                # Планеты: родитель всегда звезда — не другая планета!
                parent, _ = find_nearest_parent(entity, entities, {'star'})
                se_type = 'Planet'
                if parent is None:
                    parent = center
            if parent is None:
                parent = center
            pos_rel = vec_sub(parse_vec3(entity['Position']), parse_vec3(parent['Position']))
            vel_rel = vec_sub(parse_vec3(entity['Velocity']), parse_vec3(parent['Velocity']))
            orbit = compute_kepler_orbit(pos_rel, vel_rel, parent.get('PhysicsMass', 1e30))
            method = 'COMPUTED'
            if orbit is None:
                dist_au = max(vec_len(pos_rel) * M_TO_AU, 1e-5)
                orbit = {
                    'SemiMajorAxis_AU': dist_au, 'Eccentricity': 0.0,
                    'Inclination': 0.0, 'Period_days': 1.0,
                    'source': 'fallback',
                }
                method = 'FALLBACK'

        orbit = sanitize_orbit(orbit, se_type)
        print(f"  [{method:8s}] {name[:28]:28s} [{cat:6s}] -> {parent.get('Name','?'):15s} | SMA={orbit['SemiMajorAxis_AU']:.4f} AU")
        sc_block = entity_to_sc(entity, parent, orbit, se_type, se_star_name='Мое Солнце')
        if se_type == 'Moon':
            moon_lines.append(sc_block)
            moon_lines.append('')
        else:
            planet_lines.append(sc_block)
            planet_lines.append('')

    for entity in entities:
        _process_entity(entity)

    out_lines = header + planet_lines + moon_lines
    out_path = os.path.join(output_dir, 'catalog.sc')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))

    print(f"\nГотово: {out_path}")
    print("Скопируйте в Space Engine:")
    print("  <SE>/addons/catalogs/planets/моя_симуляция.sc")


class US2SE_Converter:
    """
    Класс-обёртка для совместимости с live_sync.py.
    Использование: converter = US2SE_Converter(se_install_dir)
                   converter.convert_ubox(ubox_path, catalog_name)
    """
    def __init__(self, se_install_dir):
        self.se_install_dir = se_install_dir
        # Выходная папка: <SE>/addons/catalogs/planets/
        self.output_base = os.path.join(se_install_dir, 'addons', 'catalogs', 'planets')

    def convert_ubox(self, ubox_path, catalog_name='US2_IMPORT', se_star_name='Sun'):
        """
        Конвертирует .ubox файл и сохраняет каталог в папку SE addons.
        ubox_path    — путь к .ubox файлу
        catalog_name — имя выходного .sc файла (без расширения)
        se_star_name — имя родительской звезды в SpaceEngine
        """
        out_dir = self.output_base
        os.makedirs(out_dir, exist_ok=True)

        # Временно переопределяем имя файла
        import zipfile, json
        with zipfile.ZipFile(ubox_path, 'r') as zf:
            with zf.open('simulation.json') as fp:
                data = json.load(fp)

        entities  = data.get('Entities', [])
        id_map    = {e['Id']: e for e in entities}
        stars     = [e for e in entities if e.get('Category') == 'star']
        center    = max(stars or entities, key=lambda e: e.get('PhysicsMass', 0))

        header = [
            f'// Сгенерировано us2se_converter.py v3.2',
            f'// Источник: {os.path.basename(ubox_path)}',
            f'// Центр: {center["Name"]}',
            '',
        ]
        planet_lines = []
        moon_lines   = []
        seen_names   = set()

        for entity in entities:
            name = entity.get('Name', '')
            cat  = entity.get('Category', '').lower()
            if not name or 'camera' in name.lower() or 'dummy' in name.lower():
                continue
            if entity['Id'] == center['Id']:
                continue
            if is_junk(entity):
                print(f"  [SKIP]  {name[:40]:40s} (мусор/фрагмент)")
                continue
            name_key = name.strip().lower()
            if name_key in seen_names:
                print(f"  [DUP]   {name[:40]:40s} (дубликат — пропущен)")
                continue
            seen_names.add(name_key)

            known = get_known_orbit(name)
            if known:
                parent_name_db = known['ParentOverride']
                parent_from_db = next(
                    (e for e in entities if e.get('Name','').strip().lower() == parent_name_db.lower()),
                    None
                )
                if parent_from_db is None:
                    if cat == 'moon':
                        parent_from_db, _ = find_nearest_parent(entity, entities, {'planet','star'})
                    parent = parent_from_db if parent_from_db else center
                else:
                    parent = parent_from_db
                orbit = {
                    'SemiMajorAxis_AU': known['SemiMajorAxis_AU'],
                    'Eccentricity':     known['Eccentricity'],
                    'Inclination':      known['Inclination'],
                    'Period_days':      known['Period_days'],
                    'source':          'NASA/JPL database',
                }
                se_type = known['SEType']
            else:
                if cat == 'moon':
                    raw_parent, _ = find_nearest_parent(entity, entities, {'planet','star'})
                    se_type, parent = resolve_se_type(cat, raw_parent, entities, center)
                elif cat == 'sso':
                    parent, _ = find_nearest_parent(entity, entities, {'star'})
                    se_type = 'Asteroid'
                    if parent is None:
                        parent = center
                else:
                    parent, _ = find_nearest_parent(entity, entities, {'star'})
                    se_type = 'Planet'
                    if parent is None:
                        parent = center
                if parent is None:
                    parent = center
                pos_rel = vec_sub(parse_vec3(entity['Position']), parse_vec3(parent['Position']))
                vel_rel = vec_sub(parse_vec3(entity['Velocity']), parse_vec3(parent['Velocity']))
                orbit   = compute_kepler_orbit(pos_rel, vel_rel, parent.get('PhysicsMass',1e30))
                if orbit is None:
                    dist_au = max(vec_len(pos_rel) * M_TO_AU, 1e-5)
                    orbit   = {'SemiMajorAxis_AU': dist_au, 'Eccentricity': 0.0,
                               'Inclination': 0.0, 'Period_days': 1.0, 'source': 'fallback'}

            orbit = sanitize_orbit(orbit, se_type)
            sc_block = entity_to_sc(entity, parent, orbit, se_type, se_star_name)
            if se_type == 'Moon':
                moon_lines.append(sc_block)
                moon_lines.append('')
            else:
                planet_lines.append(sc_block)
                planet_lines.append('')

        out_path = os.path.join(out_dir, catalog_name + '.sc')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(header + planet_lines + moon_lines))
        print(f'Каталог сохранён: {out_path} ({len(planet_lines)//2} планет, {len(moon_lines)//2} лун)')
        return out_path


if __name__ == '__main__':
    ubox_arg = sys.argv[1] if len(sys.argv) > 1 else None
    convert(ubox_arg)

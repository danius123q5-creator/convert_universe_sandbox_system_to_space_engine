import zipfile, json
with zipfile.ZipFile(r'C:\Users\PC\Documents\Universe Sandbox\Simulations\Моя симуляция.ubox', 'r') as zf:
    text = zf.read('simulation.json').decode('utf-8')
    import re
    print(list(set(re.findall(r'"[a-zA-Z0-9_]*Life[a-zA-Z0-9_]*"', text))))
    print(list(set(re.findall(r'"[a-zA-Z0-9_]*Organic[a-zA-Z0-9_]*"', text))))
    print(list(set(re.findall(r'"[a-zA-Z0-9_]*Biomass[a-zA-Z0-9_]*"', text))))
    data = json.loads(text)
    for e in data['Entities'][1:]:
        for c in e.get('Components', []):
            if c.get('$type') == 'Life':
                print(e.get('Name'), 'has Life component:', c)

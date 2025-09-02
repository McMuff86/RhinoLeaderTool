#! python 3
# -*- coding: utf-8 -*-

import os
import io


def read_kv_lines(path):
    pairs = []
    with io.open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line.strip():
                continue
            if ',' in line:
                k, v = line.split(',', 1)
                pairs.append((k.strip(), v.strip()))
            else:
                pairs.append((line.strip(), ''))
    return pairs


def write_kv_lines(path, pairs):
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        for k, v in pairs:
            f.write(f"{k},{v}\n")


def update_file(csv_path):
    pairs = read_kv_lines(csv_path)
    kv = {k: v for k, v in pairs}

    # Derive defaults
    farbe_band = kv.get('Farbe_Bandseite', '').strip()
    if not farbe_band:
        farbe_band = 'NA'

    # Rename Kantenfarbe -> Türblattkanten (preserve value)
    if 'Kantenfarbe' in kv:
        kv['Türblattkanten'] = kv.get('Kantenfarbe', 'NA')
        kv.pop('Kantenfarbe', None)

    # Ensure Türblatt_Farbe_*
    kv.setdefault('Türblatt_Farbe_Bandseite', farbe_band)
    # Futterseite fallback NA if missing
    farbe_futter = kv.get('Farbe_Futterseite', '').strip() or 'NA'
    kv.setdefault('Türblatt_Farbe_Futterseite', farbe_futter)

    # Ensure new keys with NA if missing
    for k in ['Türblatt_Falzbreite', 'Türblatt_Falztiefe']:
        kv.setdefault(k, 'NA')

    # Recreate sorted list by key
    sorted_pairs = sorted(kv.items(), key=lambda x: x[0])
    write_kv_lines(csv_path, sorted_pairs)
    return len(sorted_pairs)


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    updated = []
    for name in os.listdir(base):
        if name.lower().endswith('.csv'):
            p = os.path.join(base, name)
            try:
                n = update_file(p)
                updated.append((name, n))
            except Exception as e:
                print('Fehler beim Aktualisieren:', name, e)
    print('CSV-Dateien aktualisiert:', len(updated))
    for nm, count in updated:
        print(' -', nm, '(', count, 'Zeilen )')


if __name__ == '__main__':
    main()



import requests
import json
import time
import re
from datetime import date, datetime
import os

# ═══════════════════════════════════════════
#  НАСТРОЙКИ
# ═══════════════════════════════════════════
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

# Заголовки для Supabase REST API (работает с любым форматом ключа)
SUPA_HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
}

# ═══════════════════════════════════════════
#  SUPABASE REST API (без внешней библиотеки)
# ═══════════════════════════════════════════

def supa_select(table, columns='*', filters=None):
    url = f'{SUPABASE_URL}/rest/v1/{table}?select={columns}'
    if filters:
        url += '&' + '&'.join(f'{k}=eq.{v}' for k, v in filters.items())
    r = requests.get(url, headers=SUPA_HEADERS, timeout=30)
    return r.json() if r.status_code == 200 else []

def supa_upsert(table, rows):
    if not rows:
        return True
    url = f'{SUPABASE_URL}/rest/v1/{table}'
    headers = dict(SUPA_HEADERS)
    headers['Prefer'] = 'resolution=merge-duplicates,return=minimal'
    r = requests.post(url, headers=headers, json=rows, timeout=30)
    return r.status_code in (200, 201)

def supa_update(table, data, match_column, match_value):
    url = f'{SUPABASE_URL}/rest/v1/{table}?{match_column}=eq.{match_value}'
    r = requests.patch(url, headers=SUPA_HEADERS, json=data, timeout=30)
    return r.status_code in (200, 204)

def supa_update_many(table, data, column, values):
    """Обновляет несколько строк по списку значений"""
    if not values:
        return True
    url = f'{SUPABASE_URL}/rest/v1/{table}?{column}=in.({",".join(values)})'
    r = requests.patch(url, headers=SUPA_HEADERS, json=data, timeout=30)
    return r.status_code in (200, 204)

def test_connection():
    """Проверяем подключение к Supabase"""
    url = f'{SUPABASE_URL}/rest/v1/listings?select=id&limit=1'
    r = requests.get(url, headers=SUPA_HEADERS, timeout=10)
    if r.status_code == 200:
        print('✅ Supabase подключён')
        return True
    print(f'❌ Supabase ошибка: HTTP {r.status_code} — {r.text[:200]}')
    return False

# ═══════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════

def get_page(url, delay=2):
    try:
        time.sleep(delay)
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.text
        print(f'  HTTP {r.status_code} для {url[:60]}')
        return None
    except Exception as e:
        print(f'  Ошибка {url[:60]}: {e}')
        return None

def get_next_data(html):
    if not html:
        return None
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            return None
    return None

def find_listings_array(obj, depth=0):
    if depth > 12 or not obj:
        return None
    if isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], dict):
        keys = set(obj[0].keys())
        car_keys = {'name','title','brand','model','price','mileage','year','id','url','uid'}
        if len(keys & car_keys) >= 2:
            return obj
    if isinstance(obj, dict):
        priority = ['items','data','cars','catalog','products','list','vehicles','result','offers']
        sorted_keys = sorted(obj.keys(), key=lambda k: priority.index(k) if k in priority else 99)
        for k in sorted_keys:
            result = find_listings_array(obj[k], depth + 1)
            if result:
                return result
    return None

def clean_number(s):
    if not s:
        return None
    n = re.sub(r'[^\d]', '', str(s))
    return int(n) if n and len(n) > 1 else None

def clean_text(s):
    if not s:
        return ''
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', str(s))).strip()

def brand_from_slug(url):
    slug = url.rstrip('/').split('/')[-1]
    m = re.search(r'(?:^|-)(20[12]\d)(?:-|$)', slug)
    year = m.group(1) if m else None
    cleaned = re.sub(r'(?:^|-)(20[12]\d)(?:-|$)', '-', slug)
    parts = [p.capitalize() for p in cleaned.split('-') if p]
    return ' '.join(parts), year

def extract_year(text):
    m = re.search(r'\b(20[12]\d)\b', str(text))
    return int(m.group(1)) if m else None

def extract_mileage(text):
    m = re.search(r'(\d[\d\s]+)\s*км', str(text), re.I)
    return m.group(1).replace(' ', '') if m else None

# ═══════════════════════════════════════════
#  ПАРСЕРЫ ОФИЦИАЛЬНЫХ САЙТОВ
# ═══════════════════════════════════════════

def parse_alfa_leasing():
    items = []
    base = 'https://alfaleasing.ru'
    for page in range(1, 20):
        url = f'{base}/rasprodazha-avto-s-probegom/gruzovye/?page={page}'
        html = get_page(url, delay=2)
        if not html:
            break
        nd = get_next_data(html)
        if not nd:
            break
        catalog = find_listings_array(nd)
        if not catalog:
            break
        for car in catalog:
            eq = car.get('equipment') or {}
            make = (eq.get('make') or {}).get('name', '')
            model = eq.get('name') or eq.get('display_name') or ''
            brand = f'{make} {model}'.strip()
            lp = car.get('lot_params') or {}
            uid = car.get('uid', '')
            items.append({
                'company': 'Альфа Лизинг',
                'brand': brand or clean_text(str(car.get('description', ''))[:50]),
                'year': car.get('year'),
                'mileage': clean_number(lp.get('mileage') or car.get('mileage')),
                'price': clean_number(car.get('price')),
                'city': clean_text(car.get('city', '')),
                'vin': car.get('vin') or lp.get('vin'),
                'url': f'{base}/rasprodazha-avto-s-probegom/gruzovye/{uid}/' if uid else url,
                'source': 'alfaleasing.ru',
            })
        if len(catalog) < 12:
            break
    print(f'  Альфа Лизинг: {len(items)}')
    return items

def parse_ileasing():
    items = []
    base = 'https://www.ileasing.ru'
    seen = set()
    for cat in ['/bu_tehnika/gruzovoy-transport/', '/bu_tehnika/legkovoy-transport/']:
        for page in range(1, 10):
            url = f'{base}{cat}' + (f'?PAGEN_1={page}' if page > 1 else '')
            html = get_page(url, delay=3)
            if not html:
                break
            links = list(set(re.findall(r'href="(/bu_tehnika/[^"?#]+/[^"?#/]{5,}/?)"', html)))
            new = [l for l in links if l not in seen and
                   len(l.split('/')) >= 4 and
                   l.split('/')[-2] not in ['gruzovoy-transport','legkovoy-transport','bu_tehnika']]
            if not new:
                break
            for href in new:
                seen.add(href)
                brand, year = brand_from_slug(href)
                items.append({
                    'company': 'ИнтерЛизинг', 'brand': brand,
                    'year': int(year) if year else None,
                    'url': base + href, 'source': 'ileasing.ru',
                })
            if f'PAGEN_1={page+1}' not in html:
                break
    print(f'  ИнтерЛизинг: {len(items)}')
    return items

def parse_carcade():
    items = []
    base = 'https://www.carcade.com'
    for page in range(1, 20):
        url = f'{base}/avto_s_probegom' + (f'?page={page}' if page > 1 else '')
        html = get_page(url, delay=4)
        if not html:
            break
        nd = get_next_data(html)
        if nd:
            catalog = find_listings_array(nd)
            if catalog:
                for car in catalog:
                    cu = car.get('url') or car.get('path') or ''
                    items.append({
                        'company': 'Каркаде',
                        'brand': clean_text(car.get('name') or car.get('title') or
                                           f"{car.get('mark','')} {car.get('model','')}".strip()),
                        'year': car.get('year') or car.get('productionYear'),
                        'mileage': clean_number(car.get('mileage') or car.get('run')),
                        'price': clean_number(car.get('price') or car.get('cost')),
                        'city': clean_text(car.get('city') or car.get('region') or ''),
                        'vin': car.get('vin'),
                        'url': cu if cu.startswith('http') else base + cu,
                        'source': 'carcade.com',
                    })
                if len(catalog) < 10:
                    break
                continue
        links = list(set(re.findall(r'href="(/avto_s_probegom/\d+[^"]*)"', html)))
        if not links:
            break
        for href in links:
            items.append({'company': 'Каркаде', 'url': base + href, 'source': 'carcade.com'})
        break
    print(f'  Каркаде: {len(items)}')
    return items

def parse_sberleasing():
    items = []
    base = 'https://www.sberleasing.ru'
    for cat in ['/realizaciya-imushestva/gruzovoy-avtotransport-i-avtobusy/',
                '/realizaciya-imushestva/tyagachi/']:
        html = get_page(base + cat, delay=5)
        if not html:
            continue
        links = list(set(re.findall(
            r'href="(/realizaciya-imushestva/[^"?#]+/[^"?#/]{5,}/)"', html)))
        for href in links:
            brand, year = brand_from_slug(href)
            items.append({'company': 'СберЛизинг', 'brand': brand,
                         'year': int(year) if year else None,
                         'url': base + href, 'source': 'sberleasing.ru'})
    print(f'  СберЛизинг: {len(items)}')
    return items

def parse_vtb_leasing():
    items = []
    base = 'https://www.vtb-leasing.ru'
    html = get_page(base + '/market/', delay=4)
    if html:
        bid = re.search(r'"buildId"\s*:\s*"([^"]+)"', html)
        if bid:
            try:
                r = requests.get(
                    f'{base}/_next/data/{bid.group(1)}/market.json',
                    headers=HEADERS, timeout=10)
                if r.status_code == 200:
                    catalog = find_listings_array(r.json())
                    if catalog:
                        for car in catalog:
                            items.append({
                                'company': 'ВТБ Лизинг',
                                'brand': clean_text(car.get('name') or car.get('title') or ''),
                                'year': car.get('year'),
                                'mileage': clean_number(car.get('mileage') or car.get('run')),
                                'price': clean_number(car.get('price')),
                                'city': clean_text(car.get('city') or car.get('location') or ''),
                                'vin': car.get('vin'),
                                'url': base + (car.get('url') or car.get('path') or ''),
                                'source': 'vtb-leasing.ru',
                            })
            except:
                pass
        if not items:
            links = list(set(re.findall(r'href="(/auto/probeg/[^"?#]+)"', html)))
            for href in links:
                brand, year = brand_from_slug(href)
                items.append({'company': 'ВТБ Лизинг', 'brand': brand,
                             'year': int(year) if year else None,
                             'url': base + href, 'source': 'vtb-leasing.ru'})
    print(f'  ВТБ Лизинг: {len(items)}')
    return items

def parse_sovcom():
    items = []
    base = 'https://sovcombank-leasing.ru'
    for page in range(1, 10):
        html = get_page(f'{base}/market/used-cars?page={page}', delay=4)
        if not html:
            break
        nd = get_next_data(html)
        if nd:
            catalog = find_listings_array(nd)
            if catalog:
                for car in catalog:
                    uid = car.get('id') or car.get('uuid') or car.get('slug') or ''
                    items.append({
                        'company': 'Совком Лизинг',
                        'brand': clean_text(car.get('name') or car.get('title') or
                                           f"{car.get('brand','')} {car.get('model','')}".strip()),
                        'year': car.get('year') or car.get('productionYear'),
                        'mileage': clean_number(car.get('mileage') or car.get('run')),
                        'price': clean_number(car.get('price') or car.get('cost')),
                        'city': clean_text(car.get('city') or car.get('address') or ''),
                        'vin': car.get('vin'),
                        'url': f'{base}/market/used-cars/{uid}',
                        'source': 'sovcombank-leasing.ru',
                    })
                if len(catalog) < 10:
                    break
                continue
        break
    print(f'  Совком Лизинг: {len(items)}')
    return items

def parse_europlan():
    items = []
    base = 'https://europlan.ru'
    for cat in ['/auto/sale/truck', '/auto/sale/special']:
        html = get_page(base + cat, delay=4)
        if not html:
            continue
        bid = re.search(r'"buildId"\s*:\s*"([^"]+)"', html)
        if bid:
            try:
                r = requests.get(
                    f'{base}/_next/data/{bid.group(1)}{cat}.json',
                    headers=HEADERS, timeout=10)
                if r.status_code == 200:
                    catalog = find_listings_array(r.json())
                    if catalog:
                        for car in catalog:
                            items.append({
                                'company': 'Европлан',
                                'brand': clean_text(
                                    car.get('name') or car.get('title') or
                                    f"{car.get('markName','')} {car.get('modelName','')}".strip()),
                                'year': car.get('year') or car.get('releaseYear'),
                                'mileage': clean_number(car.get('mileage') or car.get('run')),
                                'price': clean_number(car.get('price') or car.get('cost')),
                                'city': clean_text(car.get('city') or car.get('region') or ''),
                                'vin': car.get('vin'),
                                'url': base + (car.get('url') or car.get('path') or ''),
                                'source': 'europlan.ru',
                            })
            except:
                pass
    print(f'  Европлан: {len(items)}')
    return items

def parse_baltlease():
    items = []
    base = 'https://baltlease.ru'
    for page in range(1, 15):
        url = f'{base}/secondhand/catalog-cargo/' + (f'?page={page}' if page > 1 else '')
        html = get_page(url, delay=4)
        if not html:
            break
        nd = get_next_data(html)
        if nd:
            catalog = find_listings_array(nd)
            if catalog:
                for car in catalog:
                    items.append({
                        'company': 'Балтийский Лизинг',
                        'brand': clean_text(car.get('name') or car.get('title') or ''),
                        'year': car.get('year') or car.get('productionYear'),
                        'mileage': clean_number(car.get('mileage') or car.get('run')),
                        'price': clean_number(car.get('price') or car.get('cost')),
                        'city': clean_text(car.get('city') or car.get('location') or ''),
                        'vin': car.get('vin'),
                        'url': base + (car.get('url') or car.get('path') or ''),
                        'source': 'baltlease.ru',
                    })
                if len(catalog) < 10:
                    break
                continue
        links = list(set(re.findall(r'href="(/secondhand/[^"?#]+/[^"?#/]{5,}/?)"', html)))
        links = [l for l in links if len(l.split('/')) >= 4]
        if not links:
            break
        for href in links:
            brand, year = brand_from_slug(href)
            items.append({'company': 'Балтийский Лизинг', 'brand': brand,
                         'year': int(year) if year else None,
                         'url': base + href, 'source': 'baltlease.ru'})
        if f'page={page+1}' not in html:
            break
    print(f'  Балтийский Лизинг: {len(items)}')
    return items

# ═══════════════════════════════════════════
#  AVITO (с GitHub IP — без блокировок)
# ═══════════════════════════════════════════

def parse_avito():
    items = []
    sellers = [
        ('Каркаде',           'https://www.avito.ru/brands/i52793947/all'),
        ('ВТБ Лизинг',        'https://www.avito.ru/brands/vtb-leasing'),
        ('СберЛизинг',        'https://www.avito.ru/brands/sberleasing/all'),
        ('Европлан',          'https://www.avito.ru/brands/europlan_teh'),
        ('Совком Лизинг',     'https://www.avito.ru/brands/i194762258/items/all'),
        ('Ресо Лизинг',       'https://www.avito.ru/brands/resolesing'),
        ('Балтийский Лизинг', 'https://www.avito.ru/brands/i101668348/all'),
        ('Альфа Лизинг',      'https://www.avito.ru/brands/alfaleasingtrucks/items/all/gruzoviki_i_spetstehnika'),
        ('ГПБ Автолизинг',    'https://www.avito.ru/brands/i170547328/all/transport'),
        ('Камаз Лизинг',      'https://www.avito.ru/brands/i314120110/items/all/gruzoviki_i_spetstehnika'),
        ('ИнтерЛизинг',       'https://www.avito.ru/brands/ileasing/items/all'),
        ('Восток Лизинг',     'https://www.avito.ru/brands/i192526016/all'),
        ('Реалист',           'https://www.avito.ru/brands/realistbank/all/transport'),
    ]
    for company, start_url in sellers:
        co_items = []
        for page in range(1, 10):
            url = start_url + (f'?p={page}' if page > 1 else '')
            html = get_page(url, delay=6)
            if not html or len(html) < 3000:
                print(f'  {company} (Avito): заблокировано')
                break
            nd = get_next_data(html)
            page_items = []
            if nd:
                try:
                    catalog = (
                        (nd.get('props') or {}).get('pageProps', {})
                        .get('initialState', {}).get('items', {}).get('items') or
                        find_listings_array(nd)
                    )
                    if catalog:
                        for item in catalog:
                            title = item.get('title') or item.get('name') or ''
                            price_obj = item.get('priceDetailed') or item.get('price') or {}
                            price = price_obj.get('value') if isinstance(price_obj, dict) else price_obj
                            item_url = item.get('url') or ''
                            page_items.append({
                                'company': company,
                                'brand': clean_text(title),
                                'year': item.get('year') or extract_year(title),
                                'mileage': clean_number(item.get('mileage') or extract_mileage(title)),
                                'price': clean_number(price),
                                'city': clean_text((item.get('location') or {}).get('name') or ''),
                                'vin': item.get('vin'),
                                'url': f'https://www.avito.ru{item_url}' if item_url and not item_url.startswith('http') else item_url,
                                'source': 'Avito',
                            })
                except:
                    pass
            if not page_items:
                item_links = list(set(re.findall(r'href="(/[^"?#]+_\d{8,})"', html)))
                for href in item_links:
                    title = re.sub(r'_\d+$', '', href.split('/')[-1]).replace('-', ' ').strip()
                    page_items.append({
                        'company': company,
                        'brand': title.capitalize(),
                        'url': 'https://www.avito.ru' + href,
                        'source': 'Avito',
                    })
            if not page_items:
                break
            co_items.extend(page_items)
            if len(page_items) < 20:
                break
            time.sleep(5)
        print(f'  {company} (Avito): {len(co_items)}')
        items.extend(co_items)
    return items

# ═══════════════════════════════════════════
#  ДЕДУПЛИКАЦИЯ
# ═══════════════════════════════════════════

def deduplicate(items):
    seen_vins = {}
    seen_urls = set()
    result = []
    dupes = 0
    for item in items:
        url = item.get('url', '')
        vin = (item.get('vin') or '').strip().upper()
        if url and url in seen_urls:
            dupes += 1
            continue
        if url:
            seen_urls.add(url)
        if vin and len(vin) >= 10:
            if vin in seen_vins:
                dupes += 1
                continue
            seen_vins[vin] = url
        result.append(item)
    print(f'  Дедупликация: {len(items)} → {len(result)} (дублей: {dupes})')
    return result

# ═══════════════════════════════════════════
#  СОХРАНЕНИЕ В БАЗУ
# ═══════════════════════════════════════════

def save_to_db(items):
    if not items:
        print('  Нечего сохранять')
        return

    existing = supa_select('listings', 'url,date_found')
    existing_map = {row['url']: row['date_found'] for row in (existing or [])}
    print(f'  В базе уже: {len(existing_map)} записей')

    today = str(date.today())
    now_ts = datetime.utcnow().isoformat()
    to_upsert = []

    for item in items:
        url = item.get('url', '')
        if not url:
            continue
        to_upsert.append({
            'company':      item.get('company', ''),
            'brand':        item.get('brand', ''),
            'year':         item.get('year'),
            'mileage':      item.get('mileage'),
            'price':        item.get('price'),
            'city':         item.get('city', ''),
            'url':          url,
            'source':       item.get('source', ''),
            'vin':          item.get('vin'),
            'date_found':   existing_map.get(url, today),
            'date_updated': now_ts,
            'status':       'В наличии',
        })

    # Помечаем снятые с продажи
    new_urls = {i['url'] for i in to_upsert}
    removed = [u for u in existing_map if u not in new_urls]
    if removed:
        for i in range(0, len(removed), 50):
            batch = removed[i:i+50]
            supa_update_many('listings', {'status': 'Снято с продажи', 'date_updated': now_ts},
                            'url', batch)
        print(f'  Снято с продажи: {len(removed)}')

    # Сохраняем пакетами по 50
    saved = 0
    for i in range(0, len(to_upsert), 50):
        batch = to_upsert[i:i+50]
        if supa_upsert('listings', batch):
            saved += len(batch)
        else:
            print(f'  Ошибка записи пакета {i//50 + 1}')

    print(f'  Сохранено: {saved} записей')

# ═══════════════════════════════════════════
#  ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════

def main():
    print('=' * 50)
    print('АГРЕГАТОР ЛИЗИНГОВОЙ ТЕХНИКИ')
    print(f'Запуск: {datetime.now().strftime("%d.%m.%Y %H:%M")}')
    print('=' * 50)

    if not test_connection():
        print('ОСТАНОВКА: нет подключения к базе данных')
        return

    all_items = []

    print('\n📡 Официальные сайты:')
    for parser in [parse_alfa_leasing, parse_ileasing, parse_carcade,
                   parse_sberleasing, parse_vtb_leasing, parse_sovcom,
                   parse_europlan, parse_baltlease]:
        try:
            all_items.extend(parser())
        except Exception as e:
            print(f'  Ошибка {parser.__name__}: {e}')

    print('\n📱 Avito:')
    try:
        all_items.extend(parse_avito())
    except Exception as e:
        print(f'  Ошибка Avito: {e}')

    print(f'\n📊 Всего найдено: {len(all_items)}')
    unique = deduplicate(all_items)

    print('\n💾 Сохранение в базу:')
    save_to_db(unique)

    print('\n✅ ГОТОВО!')
    print(f'Итого в базе: {len(unique)} уникальных объявлений')

if __name__ == '__main__':
    main()

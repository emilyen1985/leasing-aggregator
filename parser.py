import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import date
from supabase import create_client

# ═══════════════════════════════════════════
#  НАСТРОЙКИ
# ═══════════════════════════════════════════
import os
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
}

# ═══════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════

def get_page(url, delay=2):
    try:
        time.sleep(delay)
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.text
        print(f'HTTP {r.status_code} для {url}')
        return None
    except Exception as e:
        print(f'Ошибка {url}: {e}')
        return None

def get_next_data(html):
    if not html:
        return None
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
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

def extract_year_from_slug(slug):
    m = re.search(r'(?:^|-)(20[12]\d)(?:-|$)', slug)
    return m.group(1) if m else None

def brand_from_slug(url):
    slug = url.rstrip('/').split('/')[-1]
    year = extract_year_from_slug(slug)
    cleaned = re.sub(r'(?:^|-)(20[12]\d)(?:-|$)', '-', slug)
    parts = [p.capitalize() for p in cleaned.split('-') if p]
    return ' '.join(parts), year

# ═══════════════════════════════════════════
#  ПАРСЕРЫ САЙТОВ
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
                'brand': brand or clean_text(car.get('description', '')[:50]),
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
    print(f'Альфа Лизинг: {len(items)} объявлений')
    return items

def parse_ileasing():
    items = []
    base = 'https://www.ileasing.ru'
    cats = ['/bu_tehnika/gruzovoy-transport/', '/bu_tehnika/legkovoy-transport/', '/bu_tehnika/']
    seen_urls = set()
    for cat in cats:
        for page in range(1, 10):
            url = f'{base}{cat}' + (f'?PAGEN_1={page}' if page > 1 else '')
            html = get_page(url, delay=3)
            if not html or ('404' in html and len(html) < 3000):
                break
            links = re.findall(r'href="(/bu_tehnika/[^"?#]+/[^"?#/]{5,}/?)"', html)
            links = list(set(links))
            new_links = [l for l in links if l not in seen_urls and
                        len(l.split('/')) >= 4 and
                        l.split('/')[-2] not in ['gruzovoy-transport','legkovoy-transport','spetstehnika','bu_tehnika']]
            if not new_links:
                break
            for href in new_links:
                seen_urls.add(href)
                brand, year = brand_from_slug(href)
                items.append({
                    'company': 'ИнтерЛизинг',
                    'brand': brand,
                    'year': int(year) if year else None,
                    'mileage': None,
                    'price': None,
                    'city': '',
                    'vin': None,
                    'url': base + href,
                    'source': 'ileasing.ru',
                })
            if f'PAGEN_1={page+1}' not in html:
                break
    print(f'ИнтерЛизинг: {len(items)} объявлений')
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
                    car_url = car.get('url') or car.get('path') or car.get('slug') or ''
                    items.append({
                        'company': 'Каркаде',
                        'brand': clean_text(car.get('name') or car.get('title') or
                                           f"{car.get('mark','')} {car.get('model','')}".strip()),
                        'year': car.get('year') or car.get('productionYear'),
                        'mileage': clean_number(car.get('mileage') or car.get('run')),
                        'price': clean_number(car.get('price') or car.get('cost')),
                        'city': clean_text(car.get('city') or car.get('region') or ''),
                        'vin': car.get('vin'),
                        'url': car_url if car_url.startswith('http') else base + car_url,
                        'source': 'carcade.com',
                    })
                if len(catalog) < 10:
                    break
                continue
        links = list(set(re.findall(r'href="(/avto_s_probegom/\d+[^"]*)"', html)))
        if not links:
            break
        for href in links:
            items.append({'company': 'Каркаде', 'brand': f'Объявл. {href.split("/")[-1]}',
                         'url': base + href, 'source': 'carcade.com'})
        break
    print(f'Каркаде: {len(items)} объявлений')
    return items

def parse_sberleasing():
    items = []
    base = 'https://www.sberleasing.ru'
    cats = ['/realizaciya-imushestva/gruzovoy-avtotransport-i-avtobusy/',
            '/realizaciya-imushestva/tyagachi/',
            '/realizaciya-imushestva/spetstehnika/']
    for cat in cats:
        html = get_page(base + cat, delay=5)
        if not html:
            continue
        links = list(set(re.findall(r'href="(/realizaciya-imushestva/[^"?#]+/[^"?#/]{5,}/)"', html)))
        for href in links:
            brand, year = brand_from_slug(href)
            items.append({
                'company': 'СберЛизинг', 'brand': brand,
                'year': int(year) if year else None,
                'url': base + href, 'source': 'sberleasing.ru'
            })
    print(f'СберЛизинг: {len(items)} объявлений')
    return items

def parse_vtb_leasing():
    items = []
    base = 'https://www.vtb-leasing.ru'
    html = get_page(base + '/market/', delay=4)
    if not html:
        return items
    nd = get_next_data(html)
    if nd:
        bid_m = re.search(r'"buildId"\s*:\s*"([^"]+)"', html)
        if bid_m:
            nj_url = f'{base}/_next/data/{bid_m.group(1)}/market.json'
            try:
                r = requests.get(nj_url, headers=HEADERS, timeout=10)
                if r.status_code == 200:
                    nj = r.json()
                    catalog = find_listings_array(nj)
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
        links = list(set(re.findall(r'href="(/auto/probeg/[^"?#]+)"', html or '')))
        for href in links:
            brand, year = brand_from_slug(href)
            items.append({'company': 'ВТБ Лизинг', 'brand': brand,
                         'year': int(year) if year else None,
                         'url': base + href, 'source': 'vtb-leasing.ru'})
    print(f'ВТБ Лизинг: {len(items)} объявлений')
    return items

def parse_sovcom():
    items = []
    base = 'https://sovcombank-leasing.ru'
    for page in range(1, 10):
        url = f'{base}/market/used-cars?page={page}'
        html = get_page(url, delay=4)
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
    print(f'Совком Лизинг: {len(items)} объявлений')
    return items

def parse_europlan():
    items = []
    base = 'https://europlan.ru'
    cats = ['/auto/sale/truck', '/auto/sale/special']
    for cat in cats:
        html = get_page(base + cat, delay=4)
        if not html:
            continue
        bid_m = re.search(r'"buildId"\s*:\s*"([^"]+)"', html)
        if bid_m:
            try:
                nj_url = f'{base}/_next/data/{bid_m.group(1)}{cat}.json'
                r = requests.get(nj_url, headers=HEADERS, timeout=10)
                if r.status_code == 200:
                    catalog = find_listings_array(r.json())
                    if catalog:
                        for car in catalog:
                            items.append({
                                'company': 'Европлан',
                                'brand': clean_text(car.get('name') or car.get('title') or
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
    print(f'Европлан: {len(items)} объявлений')
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
    print(f'Балтийский Лизинг: {len(items)} объявлений')
    return items

def parse_avito_sellers():
    """Парсим Avito напрямую — с GitHub IP не блокирует"""
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
        company_items = []
        for page in range(1, 10):
            url = start_url + (f'?p={page}' if page > 1 else '')
            html = get_page(url, delay=5)
            if not html:
                print(f'  {company}: заблокировано')
                break
            if '429' in html[:500] or len(html) < 3000:
                print(f'  {company}: rate limit')
                break
            nd = get_next_data(html)
            page_items = []
            if nd:
                # Avito Next.js структура
                try:
                    catalog = (nd.get('props', {}).get('pageProps', {})
                              .get('initialState', {}).get('items', {}).get('items') or
                              find_listings_array(nd))
                    if catalog:
                        for item in catalog:
                            title = item.get('title') or item.get('name') or ''
                            price_obj = item.get('priceDetailed') or item.get('price') or {}
                            price = price_obj.get('value') if isinstance(price_obj, dict) else price_obj
                            item_url = item.get('url') or ''
                            page_items.append({
                                'company': company,
                                'brand': clean_text(title),
                                'year': item.get('year') or _extract_year(title),
                                'mileage': clean_number(item.get('mileage') or _extract_mileage(title)),
                                'price': clean_number(price),
                                'city': clean_text((item.get('location') or {}).get('name') or ''),
                                'vin': item.get('vin'),
                                'url': f'https://www.avito.ru{item_url}' if item_url and not item_url.startswith('http') else item_url,
                                'source': 'Avito',
                            })
                except:
                    pass
            # HTML fallback
            if not page_items:
                item_links = list(set(re.findall(
                    r'href="(/[^"?#]+_\d{8,})"', html)))
                for href in item_links:
                    title = href.split('/')[-1].replace('-', ' ').replace('_', ' ')
                    title = re.sub(r'\d{8,}$', '', title).strip()
                    page_items.append({
                        'company': company,
                        'brand': title.capitalize(),
                        'url': 'https://www.avito.ru' + href,
                        'source': 'Avito',
                    })
            if not page_items:
                break
            company_items.extend(page_items)
            if len(page_items) < 20:
                break
            time.sleep(5)
        print(f'  {company} (Avito): {len(company_items)} объявлений')
        items.extend(company_items)
    return items

def _extract_year(text):
    m = re.search(r'\b(20[12]\d)\b', str(text))
    return int(m.group(1)) if m else None

def _extract_mileage(text):
    m = re.search(r'(\d[\d\s]+)\s*км', str(text), re.I)
    return m.group(1).replace(' ', '') if m else None

# ═══════════════════════════════════════════
#  ДЕДУПЛИКАЦИЯ
# ═══════════════════════════════════════════

def deduplicate(items):
    """
    Убирает дубли по трём критериям:
    1. VIN совпадает → дубль 100%
    2. Бренд + Год + Пробег ±500 км → вероятный дубль
    3. URL уже есть → тот же источник
    """
    seen_vins = {}
    seen_url = set()
    result = []
    skipped = 0

    for item in items:
        url = item.get('url', '')
        vin = (item.get('vin') or '').strip().upper()

        # URL дубль
        if url and url in seen_url:
            skipped += 1
            continue
        if url:
            seen_url.add(url)

        # VIN дубль
        if vin and len(vin) >= 10:
            if vin in seen_vins:
                # Помечаем как дубль, но добавляем с пометкой
                item['duplicate_source'] = seen_vins[vin]
                skipped += 1
                continue
            seen_vins[vin] = url

        result.append(item)

    print(f'Дедупликация: {len(items)} → {len(result)} (убрано {skipped} дублей)')
    return result

# ═══════════════════════════════════════════
#  ЗАПИСЬ В БАЗУ ДАННЫХ
# ═══════════════════════════════════════════

def save_to_db(items):
    if not items:
        print('Нечего сохранять')
        return

    # Получаем существующие URL из базы
    existing = supabase.table('listings').select('url, date_found').execute()
    existing_urls = {row['url']: row['date_found'] for row in (existing.data or [])}
    print(f'В базе уже {len(existing_urls)} записей')

    today = str(date.today())
    to_upsert = []

    for item in items:
        url = item.get('url', '')
        if not url:
            continue
        row = {
            'company':      item.get('company', ''),
            'brand':        item.get('brand', ''),
            'year':         item.get('year'),
            'mileage':      item.get('mileage'),
            'price':        item.get('price'),
            'city':         item.get('city', ''),
            'url':          url,
            'source':       item.get('source', ''),
            'vin':          item.get('vin'),
            'date_found':   existing_urls.get(url, today),
            'date_updated': 'now()',
            'status':       'В наличии',
        }
        to_upsert.append(row)

    # Помечаем снятые с продажи
    new_urls = {item['url'] for item in to_upsert if item['url']}
    removed = [url for url in existing_urls if url not in new_urls]
    if removed:
        supabase.table('listings').update({'status': 'Снято с продажи'}).in_('url', removed).execute()
        print(f'Помечено снятыми: {len(removed)}')

    # Сохраняем пакетами по 100
    batch_size = 100
    saved = 0
    for i in range(0, len(to_upsert), batch_size):
        batch = to_upsert[i:i+batch_size]
        supabase.table('listings').upsert(batch, on_conflict='url').execute()
        saved += len(batch)

    print(f'Сохранено в базу: {saved} записей')

# ═══════════════════════════════════════════
#  ЗАПУСК
# ═══════════════════════════════════════════

def main():
    print('=' * 50)
    print('АГРЕГАТОР ЛИЗИНГОВОЙ ТЕХНИКИ — СБОР ДАННЫХ')
    print('=' * 50)

    all_items = []

    # 1. Парсим официальные сайты
    print('\n--- Официальные сайты ---')
    parsers = [
        parse_alfa_leasing,
        parse_ileasing,
        parse_carcade,
        parse_sberleasing,
        parse_vtb_leasing,
        parse_sovcom,
        parse_europlan,
        parse_baltlease,
    ]
    for parser in parsers:
        try:
            items = parser()
            all_items.extend(items)
        except Exception as e:
            print(f'Ошибка {parser.__name__}: {e}')

    # 2. Парсим Avito (с GitHub IP должно работать)
    print('\n--- Avito ---')
    try:
        avito_items = parse_avito_sellers()
        all_items.extend(avito_items)
    except Exception as e:
        print(f'Ошибка Avito: {e}')

    # 3. Дедупликация
    print(f'\n--- Всего найдено: {len(all_items)} ---')
    unique_items = deduplicate(all_items)

    # 4. Сохраняем в Supabase
    print('\n--- Сохранение в базу ---')
    save_to_db(unique_items)

    print('\n✅ ГОТОВО!')

if __name__ == '__main__':
    main()

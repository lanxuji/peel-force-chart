import csv
import json
import os
from datetime import datetime

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(DATA_DIR, "stock_pet_film.csv")
JSON_FILE = os.path.join(DATA_DIR, "stock_pet_film.json")

def _ensure_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'name', 'type_model', 'thickness_um', 'width_mm',
                'length_m', 'weight_kg', 'roll_no', 'batch_no',
                'corona', 'supplier', 'square_m', 'raw_text', 'created_at'
            ])

def add_record(record):
    """新增一条库存记录（只录入，不扣减）"""
    _ensure_csv()

    # 读现有最大 id
    max_id = 0
    with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                max_id = max(max_id, int(row.get('id', 0)))
            except:
                pass

    record['id'] = max_id + 1

    with open(CSV_FILE, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([
            record['id'],
            record.get('name', ''),
            record.get('type_model', ''),
            record.get('thickness_um', ''),
            record.get('width_mm', ''),
            record.get('length_m', ''),
            record.get('weight_kg', ''),
            record.get('roll_no', ''),
            record.get('batch_no', ''),
            record.get('corona', ''),
            record.get('supplier', ''),
            record.get('square_m', ''),
            record.get('raw_text', '')[:500],
            record.get('created_at', datetime.now().isoformat())
        ])

    # 同步写 JSON（方便查看）
    _sync_json()

def get_all_records():
    """读取所有记录"""
    _ensure_csv()
    records = []
    with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records

def get_stats():
    """统计信息"""
    records = get_all_records()
    total_weight = 0
    name_types = set()
    for r in records:
        try:
            total_weight += float(r.get('weight_kg', 0) or 0)
        except:
            pass
        if r.get('name'):
            name_types.add(r.get('name'))
    return {
        'total_count': len(records),
        'total_weight': total_weight,
        'name_types': len(name_types)
    }

def _sync_json():
    """同步 CSV 到 JSON"""
    records = get_all_records()
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

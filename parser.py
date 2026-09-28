import re

def parse_label_text(lines):
    """
    从 OCR 文本行中提取 PET 基膜标签字段
    支持：聚酯薄膜、防静电膜、合格证等多种版式
    """
    text = "\n".join(lines) if isinstance(lines, list) else str(lines)
    d = {
        "name": "",
        "type_model": "",
        "thickness": None,
        "width": None,
        "length_m": None,
        "weight": None,
        "roll_no": "",
        "batch_no": "",
        "corona": "",
        "supplier": "",
        "square_m": None
    }

    # 品名识别
    name_patterns = [
        (r'聚脂薄膜|聚酯薄膜|PET薄膜|PET基膜', 'PET基膜'),
        (r'防静电膜|抗静电', '防静电PET膜'),
        (r'OCA', 'OCA光学膜'),
        (r'离型膜', '离型膜'),
    ]
    for pat, val in name_patterns:
        if re.search(pat, text, re.I):
            d["name"] = val
            break

    # 型号
    type_match = re.search(r'型号[:：]?\s*(\w+)', text)
    if type_match:
        d["type_model"] = type_match.group(1)
    else:
        m = re.search(r'(TB\d|D\d{2}|CY\d+|AS\d*)', text)
        if m:
            d["type_model"] = m.group(1)

    # 厚度（支持 μm, u, mm 自动换算）
    thick_match = re.search(r'(\d+\.?\d*)\s*(μm|um|u)', text, re.I)
    if thick_match:
        d["thickness"] = float(thick_match.group(1))
    else:
        thick_mm = re.search(r'厚度[:：]?\s*(\d+\.\d+)\s*mm', text, re.I)
        if thick_mm:
            d["thickness"] = float(thick_mm.group(1)) * 1000
        else:
            spec_thick = re.search(r'(\d+\.?\d*)\s*[×xX*]\s*\d+\s*[×xX*]', text)
            if spec_thick:
                val = float(spec_thick.group(1))
                if val < 1:
                    val *= 1000
                d["thickness"] = val

    # 宽度
    width_match = re.search(r'(\d{3,4})\s*mm', text)
    if width_match:
        d["width"] = int(width_match.group(1))

    # 长度
    length_match = re.search(r'(\d{3,5})\s*m(?!\w)', text)
    if length_match:
        d["length_m"] = float(length_match.group(1))

    # 净重
    weight_match = re.search(r'净重[:：]?\s*(\d+\.?\d*)\s*kg', text, re.I)
    if weight_match:
        d["weight"] = float(weight_match.group(1))

    # 平方数
    sq_match = re.search(r'平方数[:：]?\s*(\d+\.?\d*)', text)
    if sq_match:
        d["square_m"] = float(sq_match.group(1))

    # 卷号/条码
    roll_patterns = [
        r'(H\d{6}[A-Z]\d{2}[A-Z]\d{2}[A-Z])',
        r'(\d{3,4}[A-Z]{2,3}\d{3}\d{4})',
        r'([A-Z]\d{2}\d{2}[A-Z]\d{3,})',
    ]
    for pat in roll_patterns:
        m = re.search(pat, text)
        if m:
            d["roll_no"] = m.group(1)
            break

    # 批次号
    batch_patterns = [
        r'批号[:：]\s*(\S+)',
        r'([A-Z]\d{6}[A-Z]\d{2}[A-Z]\d{2})',
        r'批次[:：]\s*(\S+)',
    ]
    for pat in batch_patterns:
        m = re.search(pat, text)
        if m:
            d["batch_no"] = m.group(1)
            break

    # 电晕
    if re.search(r'内电晕|内电', text):
        d["corona"] = "内电晕"
    elif re.search(r'外电晕|双面电晕', text):
        d["corona"] = "外电晕"

    # 供应商
    supplier_match = re.search(r'供应商[:：]\s*(\S+)', text)
    if supplier_match:
        d["supplier"] = supplier_match.group(1)

    return d

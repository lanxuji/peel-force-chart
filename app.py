import streamlit as st
import base64
import json
from datetime import datetime
from parser import parse_label_text
from ocr import ocr_image_b64
from storage import add_record, get_all_records, get_stats

st.set_page_config(page_title="PET 基膜标签录入", page_icon="📷", layout="wide")
st.title("📷 PET 基膜标签识别录入")

page = st.sidebar.selectbox("页面", ["📷 拍照录入", "📋 库存列表", "📊 统计"])

if page == "📷 拍照录入":
    st.subheader("拍照 / 上传标签")
    img = st.camera_input("拍标签") or st.file_uploader("或上传图片", type=["jpg","jpeg","png"])

    if img:
        st.image(img, width=300, caption="待识别")

        ocr_mode = st.radio("识别模式", ["占位模式(不调API)", "腾讯云OCR", "OCR.space", "本地Tesseract"])
        mode_map = {
            "占位模式(不调API)": "placeholder",
            "腾讯云OCR": "tencent",
            "OCR.space": "ocrspace",
            "本地Tesseract": "local"
        }

        if st.button("🔍 识别标签", type="primary"):
            with st.spinner("识别中..."):
                img_bytes = img.getvalue()
                img_b64 = base64.b64encode(img_bytes).decode()

                if mode_map[ocr_mode] == "placeholder":
                    sample_text = """聚酯薄膜
型号: TB1
规格: 75μm×1091mm×4050m
净重: 461.6kg
卷号: H260828B08C16N
订单号: H260828B08C16N
内电晕"""
                    lines = [l.strip() for l in sample_text.strip().split("\n") if l.strip()]
                else:
                    lines = ocr_image_b64(img_b64, mode_map[ocr_mode])

                st.session_state['ocr_lines'] = lines
                parsed = parse_label_text(lines)
                st.session_state['parsed'] = parsed
                st.success(f"识别完成，提取到 {len([v for v in parsed.values() if v])} 个字段")

        if 'parsed' in st.session_state:
            st.divider()
            st.subheader("📝 识别结果（可修改）")
            p = st.session_state['parsed']

            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("品名", p.get('name',''))
                thickness = st.number_input("厚度(μm)", value=float(p.get('thickness') or 0), step=0.1)
                width = st.number_input("宽度(mm)", value=float(p.get('width') or 0), step=1.0)
                roll_no = st.text_input("卷号/条码", p.get('roll_no',''))
            with col2:
                batch_no = st.text_input("批次号", p.get('batch_no',''))
                weight = st.number_input("净重(kg)", value=float(p.get('weight') or 0), step=0.1)
                corona = st.text_input("电晕", p.get('corona',''))
                supplier = st.text_input("供应商", p.get('supplier',''))

            with st.expander("OCR 原始文本"):
                st.write(st.session_state.get('ocr_lines', []))

            if st.button("✅ 确认录入", type="primary"):
                record = {
                    'name': name,
                    'type_model': p.get('type_model',''),
                    'thickness_um': thickness,
                    'width_mm': width,
                    'length_m': p.get('length_m', 0),
                    'weight_kg': weight,
                    'roll_no': roll_no,
                    'batch_no': batch_no,
                    'corona': corona,
                    'supplier': supplier,
                    'raw_text': "\n".join(st.session_state.get('ocr_lines', [])),
                    'created_at': datetime.now().isoformat()
                }
                add_record(record)
                st.success(f"✅ 录入成功！卷号: {roll_no}")
                st.balloons()
                del st.session_state['parsed']
                if 'ocr_lines' in st.session_state:
                    del st.session_state['ocr_lines']

elif page == "📋 库存列表":
    st.subheader("已录入的标签库存")
    records = get_all_records()
    if records:
        st.dataframe(records, use_container_width=True)
        st.caption(f"共 {len(records)} 条记录")
    else:
        st.info("暂无数据，去「拍照录入」页面添加吧")

elif page == "📊 统计":
    st.subheader("库存统计")
    stats = get_stats()
    col1, col2, col3 = st.columns(3)
    col1.metric("总卷数", stats['total_count'])
    col2.metric("总净重(kg)", f"{stats['total_weight']:.1f}")
    col3.metric("品名种类", stats['name_types'])

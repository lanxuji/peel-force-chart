# PET 基膜标签识别录入系统

拍照识别 PET 基膜标签 → 提取字段 → 录入库存表（只增不扣）

## 功能
- 📷 手机/电脑拍照或上传标签图片
- 🔍 OCR 识别（支持腾讯云/OCR.space/本地Tesseract/占位模式）
- 📝 识别结果人工确认/微调
- ✅ 一键录入库存表（CSV 存储）
- 📋 库存列表查看
- 📊 统计面板
- 🔄 防冷启动（GitHub Actions 定时访问）

## 快速开始
bash
pip install -r requirements.txt
streamlit run app.py
纯文本
打开浏览器 http://localhost:8501

## 部署到 Streamlit Cloud

1. 把代码推到 GitHub 仓库
2. 打开 https://share.streamlit.io
3. 关联仓库 → 选 `app.py` → Deploy
4. 获得公网地址

## 防冷启动

在 GitHub 仓库的 Settings → Secrets 里添加 `APP_URL`，GitHub Actions 会每 50 分钟自动访问。

## 数据

- 默认存 `stock_pet_film.csv`（同目录）
- 同步生成 `stock_pet_film.json`
- 图片不保存，识别完即弃

## OCR 配置

### 腾讯云 OCR（推荐，1000次/月免费）
设置环境变量：
TENCENT_SECRET_ID=xxx
TENCENT_SECRET_KEY=xxx
纯文本
### OCR.space（免费）
无需配置，直接选模式即可

### 本地 Tesseract
需安装 tesseract-ocr 并加入 PATH

## 标签格式

支持：聚酯薄膜、防静电膜、OCA、离型膜等工业标签
字段：品名、型号、厚度(μm)、宽度(mm)、长度(m)、净重(kg)、卷号、批次号、电晕、供应商

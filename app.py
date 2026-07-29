import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as ExcelImage
import os

# ==========================================
# 第一步：生成曲线图片（保持之前的逻辑）
# ==========================================
print("正在生成曲线图片...")
np.random.seed(42) # 保证每次生成的图片一样，方便核对

def generate_curve_data(target_mean, base_dev=30, end_pos=200):
    """生成单条符合物理规律的剥离力曲线"""
    x = np.arange(0, end_pos + 1)
    y = np.zeros_like(x, dtype=float)
    
    # 基础波动
    dev = base_dev + np.random.normal(0, 5)
    current_val = target_mean * 0.1 # 起始点
    
    # 状态机：0-爬升，1-稳定波动，2-下降
    state = 0
    peak_target = target_mean * (1 + np.random.uniform(-0.1, 0.1))
    
    for j in range(len(x)):
        if j < 20: # 0-20mm 自然爬升
            current_val += (peak_target * 0.8 - current_val) * 0.1
            state = 0
        elif j < 40: # 平稳过渡
            current_val += (peak_target - current_val) * 0.05
            if abs(current_val - peak_target) < 0.5:
                state = 1
        elif j < 160: # 40-160mm 有效波动区
            # 模拟真实测试的微小抖动
            noise = np.random.normal(0, target_mean * dev / 100 * 0.5)
            current_val = peak_target + noise
            # 偶尔有个小起伏
            if np.random.rand() > 0.95:
                current_val *= 1.05
            state = 1
        else: # 160mm后下降
            current_val *= 0.9
            if j > 180:
                current_val *= 0.8
            
        y[j] = max(0, current_val) # 不能为负
        
    return x, y

# 生成3条数据：8, 8, 9
curves_data = []
means = [8, 8, 9]
colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
img_filename = "temp_curve_for_excel.png"

fig, ax = plt.subplots(figsize=(10, 5), dpi=150)

for i, mean_val in enumerate(means):
    x, y = generate_curve_data(mean_val)
    curves_data.append({"id": i+1, "mean": mean_val, "max": round(np.max(y),2), "min": round(np.min(y),2), "avg": round(np.mean(y),2)})
    ax.plot(x, y, color=colors[i], linewidth=1.5, label=f'Plot {i+1} (μ={mean_val})')

# 添加辅助线和样式
ax.axvline(x=40, color='gray', linestyle=':', linewidth=1)
ax.axvline(x=160, color='gray', linestyle=':', linewidth=1)
ax.set_xlabel("变形 (mm)")
ax.set_ylabel("剥离力 (gf)")
ax.set_title("剥离力测试曲线")
ax.grid(True, linestyle='--', alpha=0.5)
ax.legend()
plt.tight_layout()
plt.savefig(img_filename)
plt.close()

print(f"图片已生成: {img_filename}")

# ==========================================
# 第二步：创建 Excel 报告
# ==========================================
print("正在生成 Excel 文件...")

wb = Workbook()
ws = wb.active
ws.title = "剥离试验报告"

# 1. 设置列宽
ws.column_dimensions['A'].width = 15
ws.column_dimensions['B'].width = 20

# 2. 定义样式
title_font = Font(name='宋体', size=16, bold=True, color="000000")
header_font = Font(name='宋体', size=11, bold=True)
normal_font = Font(name='宋体', size=10)
center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
left_align = Alignment(horizontal='left', vertical='center', wrap_text=True)

# 3. 顶部标题
ws.merge_cells('A1:B1')
ws['A1'] = "东莞市裕达新材料有限公司"
ws['A1'].font = title_font
ws['A1'].alignment = center_align

ws.merge_cells('A2:B2')
ws['A2'] = "剥离试验报告"
ws['A2'].font = Font(name='宋体', size=14, bold=True)
ws['A2'].alignment = center_align

# 4. 测试条件表格
conditions = [
    ["客户名称", "基顺隆"],
    ["材料名称", "Material-Test"],
    ["试验日期", "2024-08-05 10:14:49"],
    ["试验标准", "GB2792-2014 胶粘带剥离强度的测试方法"],
    ["试验速度", "300.000mm/min"],
    ["", ""] # 空行
]

current_row = 4
for cond in conditions:
    c1 = ws.cell(row=current_row, column=1, value=cond[0])
    c1.font = normal_font
    c1.alignment = left_align
    
    c2 = ws.cell(row=current_row, column=2, value=cond[1])
    c2.font = normal_font
    c2.alignment = left_align
    current_row += 1

# 5. 插入图片
try:
    img = ExcelImage(img_filename)
    # 调整图片大小以适应页面，并留出边距
    img.width = 500
    img.height = 250
    # 将图片放置在 D 列附近，跨列居中
    ws.add_image(img, 'D5')
    ws.merge_cells('D5:F10') # 合并单元格给图片留空间
    ws['D5'].alignment = Alignment(horizontal='center', vertical='center')
except Exception as e:
    print(f"插入图片失败: {e}")
    ws['D5'] = "图片插入失败"

# 6. 统计数据表格
data_start_row = 12
ws.merge_cells('A12:D12')
ws['A12'] = "测试数据统计"
ws['A12'].font = header_font
ws['A12'].alignment = center_align

# 表头
headers = ["No.", "目标均值(gf)", "实测最大(gf)", "实测平均(gf)"]
for col_num, header in enumerate(headers, 1):
    cell = ws.cell(row=data_start_row + 1, column=col_num, value=header)
    cell.font = header_font
    cell.alignment = center_align
    cell.fill = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid") # 浅蓝背景

# 填充数据
for i, data in enumerate(curves_data):
    row_idx = data_start_row + 2 + i
    ws.cell(row=row_idx, column=1, value=f"Plot {data['id']}").alignment = center_align
    ws.cell(row=row_idx, column=2, value=data['mean']).alignment = center_align
    ws.cell(row=row_idx, column=3, value=data['max']).alignment = center_align
    ws.cell(row=row_idx, column=4, value=data['avg']).alignment = center_align

# 保存
excel_filename = "剥离试验报告_样本.xlsx"
wb.save(excel_filename)

# 清理临时图片
if os.path.exists(img_filename):
    os.remove(img_filename)

print(f"✅ 成功生成 Excel 报告: {excel_filename}")

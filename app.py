import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

# ---------------------- 页面基础配置 ----------------------
st.set_page_config(page_title="剥离力曲线图生成器", layout="wide")
plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Zen Hei']
plt.rcParams['axes.unicode_minus'] = False

# ---------------------- 曲线生成函数 ----------------------
def build_force_curve(x, base_mean, wave_ratio, drop_start_x=180, x_s1=40):
    y = np.zeros_like(x)
    wave_amp = base_mean * wave_ratio

    # 0 ~ 20mm 快速上升
    mask_rise_fast = x <= 20
    y[mask_rise_fast] = np.linspace(0, base_mean, np.sum(mask_rise_fast))

    # 20 ~ 40mm 震荡缓慢趋于平稳
    mask_rise_slow = (x > 20) & (x <= x_s1)
    n_slow = np.sum(mask_rise_slow)
    trend_slow = np.linspace(base_mean * 0.92, base_mean, n_slow)
    trend_slow += np.random.normal(0, wave_amp * 0.5, n_slow)
    y[mask_rise_slow] = trend_slow

    # 40 ~ 160mm 核心稳定波动区
    mask_flat = (x > x_s1) & (x <= 160)
    n_flat = np.sum(mask_flat)
    y_flat = base_mean + np.random.normal(0, wave_amp, n_flat)
    y[mask_flat] = y_flat

    # 160 ~ 180mm 平稳+末端小峰值
    mask_peak = (x > 160) & (x <= drop_start_x)
    n_peak = np.sum(mask_peak)
    trend_peak = np.linspace(base_mean, base_mean * 1.06, n_peak)
    trend_peak += np.random.normal(0, wave_amp * 0.8, n_peak)
    y[mask_peak] = trend_peak

    # 180 ~ 200mm 断崖下跌
    mask_drop = (x > drop_start_x) & (x <= 200)
    n_drop = np.sum(mask_drop)
    y[mask_drop] = np.linspace(base_mean * 1.06, 0.3, n_drop)

    # 200 ~ 220mm 底部微小抖动
    mask_bottom = x > 200
    y[mask_bottom] = 0.3 + np.random.normal(0, 0.12, np.sum(mask_bottom))
    return y

# ---------------------- 侧边栏参数输入 ----------------------
st.sidebar.header("⚙ 参数设置")
seed = st.sidebar.number_input("随机种子(固定=曲线不变)", value=42)
mean1 = st.sidebar.number_input("Plot1 均值", value=18.0)
mean2 = st.sidebar.number_input("Plot2 均值", value=15.0)
mean3 = st.sidebar.number_input("Plot3 均值", value=23.0)
wave_ratio = st.sidebar.slider("波动比例", min_value=0.05, max_value=0.60, value=0.35)
regen_btn = st.sidebar.button("🔄 重新随机生成曲线")

# 固定配置
x_s1 = 40
x_e15 = 160
drop_start_x = 180
x_max_total = 220
num_points = 900

# 随机种子刷新
np.random.seed(seed if not regen_btn else None)
x = np.linspace(0, x_max_total, num_points)

# 生成三条曲线
y1 = build_force_curve(x, mean1, wave_ratio)
y2 = build_force_curve(x, mean2, wave_ratio)
y3 = build_force_curve(x, mean3, wave_ratio)

# ---------------------- 绘图 ----------------------
fig, ax = plt.subplots(figsize=(15, 8.5), dpi=120)
ax.plot(x, y1, c='#d42222', lw=1.1, label='Plot 1')
ax.plot(x, y2, c='#1a1a1a', lw=1.1, label='Plot 2')
ax.plot(x, y3, c='#27a646', lw=1.1, label='Plot 3')

# 标记虚线 s1、e15
ax.axvline(x=x_s1, color='#0033dd', linestyle='--', lw=1.2)
ax.axvline(x=x_e15, color='#0033dd', linestyle='--', lw=1.2)
max_y = np.max([y1, y2, y3])
ax.text(x_s1 + 2, max_y * 0.96, 's1', fontsize=9, color='#002299')
ax.text(x_e15 + 2, max_y * 0.96, 'e15', fontsize=9, color='#002299')

ax.set_xlabel("变形 (mm)")
ax.set_ylabel("荷重 (gf)")
ax.set_xlim(0, x_max_total)
ax.set_xticks(np.arange(0, x_max_total + 1, 20))

# Y轴：间隔固定2，上下限自适应
all_data = np.concatenate([y1, y2, y3])
y_min = 0
y_max = np.ceil(np.max(all_data) + 1.5)
ax.set_ylim(y_min, y_max)
ax.yaxis.set_major_locator(MultipleLocator(2))

ax.grid(True, color='#5499dd', alpha=0.38)
ax.set_facecolor("#c5e2ea")
ax.legend(loc='upper left')

# 页面展示
st.title("剥离试验曲线图生成工具")
st.pyplot(fig)

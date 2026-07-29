"""
==============================================================================
  剥离力曲线生成器 —— Streamlit 版
  ----------------------------------------------------------------------------
  运行方式:
    pip install streamlit matplotlib numpy pandas
    streamlit run app.py

  功能:
    - 输入 N 条曲线参数(均值/偏差/模式/终结x)
    - 点击按钮即时生成图表
    - 支持手动输入 / CSV 批量导入 / 50条预设
    - 一键导出 PNG / CSV 数据
    - 手机浏览器也能用(响应式)
==============================================================================
"""

import io
import csv
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
import streamlit as st
import pandas as pd

# ══════════════════════════════════════════════════════════════════════════
# 页面配置
# ══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="剥离力曲线生成器",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════
# 核心引擎（和原脚本一致）
# ══════════════════════════════════════════════════════════════════════════

def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)

def make_curve(target_mean, dev_percent, drop_mode='smooth', end_x=200, seed=42, x=None):
    """生成一条仿真剥离力曲线"""
    if x is None:
        x = np.arange(0, 220.5, 0.5)

    rng = np.random.RandomState(seed)
    n = len(x)

    plateau_e = 160.0
    x_de = min(end_x, 220)

    w_rise = smoothstep((x - 2.0) / (20.0 - 2.0))
    w_fall = smoothstep((x_de - x) / (x_de - plateau_e)) if x_de > plateau_e else np.zeros(n)
    w_plateau = w_rise * w_fall

    i = np.arange(n)
    wave  = 1.0  * np.sin(2 * np.pi * i / 17 + seed * 0.17)
    wave += 0.50 * np.sin(2 * np.pi * i / 6  + seed * 0.41)
    wave += 0.25 * np.sin(2 * np.pi * i / 2.5 + seed * 0.63)
    wave += 0.12 * np.sin(2 * np.pi * i / 1.2 + seed * 0.89)
    wave = wave / (np.abs(wave).max() + 1e-9)

    noise = rng.randn(n)
    raw = 0.30 * noise + 0.70 * wave

    plateau_mask = (x >= 40.0) & (x <= plateau_e)
    raw_in_plateau = raw[plateau_mask]
    allowed_half = target_mean * (dev_percent / 100.0)
    scale = (allowed_half * 0.75) / (np.abs(raw_in_plateau).max() + 1e-9)

    swing = raw * scale
    env = 0.10 + 0.90 * w_plateau
    swing = swing * env

    trend = target_mean * w_plateau

    t_rise = (x - 2.0) / (20.0 - 2.0)
    overshoot = target_mean * 0.03 * np.exp(-5 * t_rise)
    overshoot = overshoot * smoothstep(t_rise) * (x < 25.0)

    y = trend + swing + overshoot

    plateau_idx = np.where(plateau_mask)[0]
    y_plateau = y[plateau_idx]
    deviation = y_plateau - target_mean
    max_dev = np.max(np.abs(deviation))
    if max_dev > allowed_half:
        y[plateau_idx] = target_mean + deviation * (allowed_half / (max_dev + 1e-9))

    falling_mask = (x > plateau_e) & (x < x_de)

    if drop_mode == 'peak':
        peak_pos = rng.uniform(plateau_e + 3, plateau_e + (x_de - plateau_e) * 0.5)
        peak_width = rng.uniform(3, 8)
        peak_amp = target_mean * rng.uniform(0.25, 0.55)
        peak = peak_amp * np.exp(-0.5 * ((x - peak_pos) / peak_width) ** 2) * falling_mask
        y = y + peak
        post_peak = (x >= peak_pos) & (x < x_de)
        y[post_peak] = y[post_peak] * (1 - 0.85 * smoothstep((x[post_peak] - peak_pos) / max(x_de - peak_pos, 1)))
        y = y + target_mean * 0.08 * rng.randn(n) * falling_mask
    elif drop_mode == 'smooth':
        post_plateau = (x >= plateau_e) & (x < x_de)
        fall_w = smoothstep((x - plateau_e) / max(x_de - plateau_e, 1))
        y[post_plateau] = y[post_plateau] * (1 - 0.90 * fall_w[post_plateau])
        y = y + target_mean * 0.05 * rng.randn(n) * falling_mask
    elif drop_mode == 'cut':
        cut_mask = (x >= plateau_e) & (x < x_de)
        cut_w = smoothstep((x - plateau_e) / max(x_de - plateau_e, 1))
        y[cut_mask] = y[cut_mask] * (1 - 0.95 * cut_w[cut_mask])

    y[x >= x_de] = 0.15 * rng.rand((x >= x_de).sum())
    y[x < 2.0] = 0.1 * rng.rand((x < 2.0).sum())

    kernel = np.ones(5) / 5.0
    y_smooth = np.convolve(y, kernel, mode='same')
    trans_mask = (w_plateau > 0.01) & (w_plateau < 0.80)
    y[trans_mask] = y_smooth[trans_mask]

    return np.maximum(y, 0), x


# ══════════════════════════════════════════════════════════════════════════
# 配色方案
# ══════════════════════════════════════════════════════════════════════════

base_colors = [
    '#1c1c1c', '#c41e3a', '#006400', '#1f5fa6', '#e8850c',
    '#7b2d8e', '#008b8b', '#c71585', '#556b2f', '#8b4513',
]

def get_color(idx):
    if idx < len(base_colors):
        return base_colors[idx]
    base = base_colors[idx % len(base_colors)]
    r, g, b = int(base[1:3], 16), int(base[3:5], 16), int(base[5:7], 16)
    offset = (idx // len(base_colors)) * 25
    r = min(255, max(0, r + offset - 50))
    g = min(255, max(0, g + offset - 50))
    b = min(255, max(0, b + offset - 50))
    return f'#{r:02x}{g:02x}{b:02x}'


# ══════════════════════════════════════════════════════════════════════════
# 绘图函数
# ══════════════════════════════════════════════════════════════════════════

def draw_chart(curves_config):
    """根据曲线配置列表，绘制图表，返回 (fig, 统计信息)"""
    x = np.arange(0, 220.5, 0.5)
    curves_data = {}

    for ci, cfg in enumerate(curves_config):
        mean = cfg['mean']
        dev = cfg['dev']
        mode = cfg.get('mode', 'smooth')
        endx = cfg.get('end', 200)
        seed = cfg.get('seed', 42 + ci * 97)
        label = cfg.get('label', f"#{ci+1}")

        y, _ = make_curve(mean, dev, drop_mode=mode, end_x=endx, seed=seed, x=x)
        curves_data[label] = (x, y, mode, endx, mean, dev)

    # Y 轴适配
    all_y = []
    stats = []
    for label, (xx, yy, mode, ex, mc, dc) in curves_data.items():
        mask = (xx >= 40.0) & (xx <= 160.0)
        py = yy[mask]
        mv = py.mean()
        mxv = py.max()
        mnv = py.min()
        dev_pct = max(abs(mxv - mv), abs(mnv - mv)) / mv * 100
        stats.append({
            'label': label, 'target': mc, 'actual_mean': mv,
            'max': mxv, 'min': mnv, 'dev_pct': dev_pct,
            'status': 'OK' if dev_pct <= dc else 'WARN', 'mode': mode
        })
        valid = yy[(yy > 0.05) & (xx <= 160.0)]
        if len(valid) > 0:
            all_y.extend(valid)

    y_max_data = max(all_y) if all_y else 1.0
    y_top = y_max_data * 1.20

    raw_step = y_top / 10
    if raw_step < 0.05:
        candidates = [0.02, 0.05, 0.1, 0.2, 0.5]
    elif raw_step < 0.1:
        candidates = [0.05, 0.1, 0.2, 0.5, 1]
    elif raw_step < 0.5:
        candidates = [0.1, 0.2, 0.5, 1, 2]
    elif raw_step < 1:
        candidates = [0.2, 0.5, 1, 2, 5]
    elif raw_step < 5:
        candidates = [0.5, 1, 2, 5, 10]
    elif raw_step < 10:
        candidates = [1, 2, 5, 10, 20]
    else:
        candidates = [5, 10, 20, 50, 100, 200, 500]

    major_step = candidates[0]
    for s in candidates:
        if s >= raw_step * 0.6:
            major_step = s
            break

    n_ticks = y_top / major_step
    if n_ticks < 5:
        idx = candidates.index(major_step) if major_step in candidates else 2
        if idx > 0: major_step = candidates[idx - 1]
    elif n_ticks > 15:
        idx = candidates.index(major_step) if major_step in candidates else 2
        if idx < len(candidates) - 1: major_step = candidates[idx + 1]

    y_top_r = np.ceil(y_top / major_step) * major_step

    if major_step >= 1:
        minor_step = major_step / 5.0 if major_step >= 10 else major_step / 2.0
    else:
        minor_step = major_step / 5.0

    if major_step < 0.1:
        tick_fmt = lambda v: f'{v:.3f}'
    elif major_step < 0.5:
        tick_fmt = lambda v: f'{v:.2f}'
    elif major_step < 2:
        tick_fmt = lambda v: f'{v:.1f}'
    else:
        tick_fmt = lambda v: f'{int(v)}'

    ytick_vals = []
    v = 0.0
    while v <= y_top_r + 1e-9:
        ytick_vals.append(round(v, 4))
        v += major_step

    # ── 绘图 ──
    n_curves = len(curves_data)
    line_width = 1.05 if n_curves <= 10 else 0.85
    fig_h = max(5.5, min(9.0, 4.5 + n_curves * 0.07))

    fig, ax = plt.subplots(figsize=(10.5, fig_h), dpi=150)
    bg_color = '#eaf2fa'
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    legend_elements = []

    for idx, (label, (xx, yy, mode, ex, mc, dc)) in enumerate(curves_data.items()):
        color = get_color(idx)
        ax.plot(xx, yy, color=color, linewidth=line_width, label=label, zorder=3, solid_capstyle='round')

        if n_curves <= 15:
            step = max(1, len(xx) // 30)
            ax.scatter(xx[::step], yy[::step], color=color, marker='^', s=5, zorder=4, edgecolors='none')

        legend_elements.append(Line2D([0], [0], color=color, marker='^',
                                      markerfacecolor=color, markeredgecolor=color,
                                      markersize=5, linewidth=1.2, label=label))

    ax.grid(True, which='major', linestyle='-', linewidth=0.55, color='#a8c8e0', zorder=0)
    ax.grid(True, which='minor', linestyle='-', linewidth=0.25, color='#cfe0f0', zorder=0)
    ax.set_axisbelow(True)

    ax.set_xlim(0, 220)
    ax.set_xticks(np.arange(0, 221, 20))
    ax.xaxis.set_major_locator(mticker.MultipleLocator(20))
    ax.xaxis.set_minor_locator(mticker.MultipleLocator(5))

    ax.set_ylim(0, y_top_r)
    ax.set_yticks(ytick_vals)
    ax.yaxis.set_major_locator(mticker.FixedLocator(ytick_vals))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: tick_fmt(v)))
    if minor_step >= 0.001:
        ax.yaxis.set_minor_locator(mticker.MultipleLocator(minor_step))

    ax.tick_params(axis='y', which='major', labelsize=9.5, colors='#111', length=5, width=1.2)
    ax.tick_params(axis='y', which='minor', length=2.5, width=0.5, colors='#999')
    ax.tick_params(axis='x', which='major', labelsize=9.5, colors='#333', length=4, width=1)
    ax.tick_params(axis='x', which='minor', length=2, width=0.5, colors='#999')

    ax.set_xlabel('变形 (mm)', fontsize=12, fontweight='bold', color='#1a1a1a', labelpad=6)
    ax.set_ylabel('荷重 (gf)', fontsize=12, fontweight='bold', color='#1a1a1a', labelpad=6)

    for spine in ax.spines.values():
        spine.set_linewidth(1.4)
        spine.set_color('#3a3a3a')

    for mx, mlabel in [(40, 's15'), (160, 'e15')]:
        ax.axvline(x=mx, color='#1f5fa6', linestyle='--', linewidth=0.9, zorder=2)
        ax.text(mx, y_top_r * 0.96, mlabel, fontsize=10, fontweight='bold',
                color='#1f5fa6', ha='center', va='bottom')

    if n_curves <= 10:
        ncol, fsize = 1, 9
    elif n_curves <= 25:
        ncol, fsize = 2, 8
    else:
        ncol, fsize = 3, 7

    legend = ax.legend(
        handles=legend_elements,
        loc='upper left', bbox_to_anchor=(0.01, 0.98),
        fontsize=fsize, frameon=True, fancybox=False,
        edgecolor='#888888', facecolor=bg_color,
        framealpha=0.92, borderpad=0.6,
        labelspacing=0.4, handlelength=1.5, handleheight=0.8,
        ncol=ncol,
    )
    legend.get_frame().set_linewidth(0.8)

    plt.subplots_adjust(left=0.10, right=0.97, top=0.96, bottom=0.11)
    plt.close()

    return fig, stats


# ══════════════════════════════════════════════════════════════════════════
# Streamlit UI
# ══════════════════════════════════════════════════════════════════════════

# ── 侧边栏：数据输入 ──
st.sidebar.title("📊 剥离力曲线生成器")
st.sidebar.markdown("---")

input_method = st.sidebar.radio(
    "选择输入方式",
    ["手动输入", "CSV 批量导入", "示例数据(5条)", "示例数据(50条)"],
    index=0,
)

curves_config = []

if input_method == "手动输入":
    st.sidebar.markdown("### 添加曲线")
    n_curves = st.sidebar.number_input("曲线数量", min_value=1, max_value=50, value=3, step=1)

    for i in range(n_curves):
        with st.sidebar.expander(f"曲线 #{i+1}", expanded=(i < 5)):
            mean = st.number_input(f"目标均值(gf)", value=round(2.5 + i*0.2, 3),
                                   min_value=0.001, step=0.001, key=f"m_{i}", format="%.3f")
            dev = st.number_input(f"偏差(%)", value=30, min_value=1, max_value=100,
                                  step=1, key=f"d_{i}")
            mode = st.selectbox(f"下降模式", ["peak", "smooth", "cut"],
                                index=1, key=f"mo_{i}")
            endx = st.number_input(f"终结位置(mm)", value=200, min_value=160, max_value=220,
                                   step=5, key=f"e_{i}")
            seed = st.number_input(f"随机种子(可选)", value=42+i*97, step=1, key=f"s_{i}")

            curves_config.append({
                'mean': mean, 'dev': dev, 'mode': mode,
                'end': endx, 'seed': seed, 'label': f"#{i+1}"
            })

elif input_method == "CSV 批量导入":
    st.sidebar.markdown("### CSV 格式说明")
    st.sidebar.code("均值,偏差%,模式,终结x\n2.545,50,peak,205\n2.346,30,smooth,200")
    uploaded = st.sidebar.file_uploader("上传 CSV 文件", type=['csv'])

    if uploaded is not None:
        content = uploaded.read().decode('utf-8').strip().split('\n')
        for i, line in enumerate(content):
            parts = line.strip().split(',')
            if not parts or parts[0].startswith('#'):
                continue
            try:
                curves_config.append({
                    'mean': float(parts[0]),
                    'dev': float(parts[1]),
                    'mode': parts[2].strip() if len(parts) > 2 else 'smooth',
                    'end': float(parts[3]) if len(parts) > 3 else 200,
                    'seed': 42 + i * 97,
                    'label': f"#{i+1}"
                })
            except ValueError:
                st.sidebar.error(f"第 {i+1} 行解析失败: {line}")

        st.sidebar.success(f"✅ 已读取 {len(curves_config)} 条曲线")
    else:
        st.sidebar.info("请上传 CSV 文件")

elif input_method == "示例数据(5条)":
    curves_config = [
        {'mean': 2.545, 'dev': 50, 'mode': 'peak',   'end': 205, 'seed': 42,   'label': '#1'},
        {'mean': 2.346, 'dev': 30, 'mode': 'smooth', 'end': 200, 'seed': 139,  'label': '#2'},
        {'mean': 2.112, 'dev': 20, 'mode': 'smooth', 'end': 195, 'seed': 236,  'label': '#3'},
        {'mean': 2.000, 'dev': 40, 'mode': 'cut',    'end': 200, 'seed': 333,  'label': '#4'},
        {'mean': 1.989, 'dev': 60, 'mode': 'peak',   'end': 210, 'seed': 430,  'label': '#5'},
    ]

elif input_method == "示例数据(50条)":
    np.random.seed(7)
    modes_list = ['peak', 'smooth', 'cut']
    for i in range(50):
        curves_config.append({
            'mean': round(np.random.uniform(1.5, 4.0), 3),
            'dev': round(np.random.uniform(10, 60), 0),
            'mode': modes_list[i % 3],
            'end': round(np.random.uniform(190, 210), 0),
            'seed': 42 + i * 97,
            'label': f"#{i+1}"
        })

# ── 主界面 ──
st.title("📊 剥离力曲线生成器")

if not curves_config:
    st.info("👈 请在左侧选择输入方式并填写数据")
    st.stop()

col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 3])

with col_btn1:
    generate = st.button("🚀 生成曲线", type="primary", use_container_width=True)

with col_btn2:
    st.download_button(
        label="📥 下载 CSV 模板",
        data="均值,偏差%,模式,终结x\n2.545,50,peak,205\n2.346,30,smooth,200\n".encode(),
        file_name="curves_template.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ── 生成图表 ──
if generate or input_method.startswith("示例"):
    with st.spinner(f"正在生成 {len(curves_config)} 条曲线..."):
        fig, stats = draw_chart(curves_config)

    # 显示图表
    st.pyplot(fig, use_container_width=True)

    # 导出 PNG
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=160, bbox_inches='tight', facecolor='#eaf2fa')
    buf.seek(0)

    col_dl1, col_dl2, _ = st.columns([1, 1, 3])
    with col_dl1:
        st.download_button(
            label="💾 下载 PNG 图片",
            data=buf.getvalue(),
            file_name="peel_force_chart.png",
            mime="image/png",
            use_container_width=True,
        )

    # 导出数据为 CSV
    x = np.arange(0, 220.5, 0.5)
    csv_buf = io.StringIO()
    writer = csv.writer(csv_buf)
    header = ['变形(mm)'] + [s['label'] for s in stats]
    writer.writerow(header)
    for j in range(len(x)):
        row = [f"{x[j]:.1f}"]
        for i, s in enumerate(stats):
            # 重新生成对应曲线数据用于导出
            y, _ = make_curve(
                s['target'], s['dev_pct'] * 2,  # dev 用实际偏差近似
                drop_mode=s['mode'],
                end_x=200, seed=42+i*97, x=x
            )
            row.append(f"{y[j]:.4f}")
        writer.writerow(row)

    with col_dl2:
        st.download_button(
            label="📊 下载数据 CSV",
            data=csv_buf.getvalue().encode(),
            file_name="curves_data.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ── 统计表格 ──
    st.markdown("### 📋 统计验证")
    df_stats = pd.DataFrame([
        {
            '曲线': s['label'],
            '目标均值': s['target'],
            '实际均值': round(s['actual_mean'], 3),
            '最大值': round(s['max'], 3),
            '最小值': round(s['min'], 3),
            '偏离%': round(s['dev_pct'], 2),
            '状态': '✅' if s['status'] == 'OK' else '⚠️',
            '模式': s['mode'],
        } for s in stats
    ])
    st.dataframe(df_stats, use_container_width=True, hide_index=True)

    ok_count = sum(1 for s in stats if s['status'] == 'OK')
    warn_count = len(stats) - ok_count
    if warn_count > 0:
        st.warning(f"⚠️ {warn_count} 条曲线偏离超出设定范围")
    else:
        st.success(f"✅ 全部 {ok_count} 条曲线通过验证")

# ── 使用说明（折叠）──
with st.expander("📖 使用说明"):
    st.markdown("""
    ### 快速开始
    1. **左侧选择输入方式**：手动输入 / CSV 导入 / 示例数据
    2. **填写每条曲线的参数**：
       - **目标均值**：曲线在 40-160mm 区域的平均荷重值(gf)
       - **偏差%**：允许的最大波动范围（如 30 表示 ±30%）
       - **下降模式**：
         - `peak` = 160mm 后有尖峰再降（模拟断裂弹跳）
         - `smooth` = 160mm 后平滑下降
         - `cut` = 160mm 后快速切断式下降
       - **终结位置**：曲线归零的 x 位置(mm)
    3. 点击 **生成曲线** 按钮
    4. 使用 **下载 PNG** 导出图片，**下载数据 CSV** 导出原始数据

    ### CSV 格式
    ```
    均值,偏差%,模式,终结x
    2.545,50,peak,205
    2.346,30,smooth,200
    2.112,20,smooth,195
    ```

    ### 部署到手机使用
    1. 注册 GitHub 账号，上传本文件
    2. 打开 share.streamlit.io，登录 GitHub
    3. 选择仓库，点 Deploy
    4. 获得公网网址，手机浏览器打开即可使用
    """)

# ── 页脚 ──
st.markdown("---")
st.caption("剥离力曲线生成器 v1.0 · 基于 Streamlit + Matplotlib")

"""
剥离试验曲线生成器 — Streamlit Web App
上传到 GitHub 后可直接部署到 Streamlit Cloud
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.ndimage import uniform_filter1d
import pandas as pd
import io
import base64

# ============================================================
# 曲线生成核心函数
# ============================================================
def generate_curves(input_values, fluctuation_pct=0.20, seed=None):
    """生成三条剥离试验曲线，返回 (x, all_curves, stats_df, raw_df)"""

    num_groups = len(input_values)
    total_length_mm = 220.0
    rise_end_mm = 20.0
    fall_start_mm = 160.0
    points_per_mm = 8

    if seed is not None:
        rng_global = np.random.RandomState(seed)
    else:
        rng_global = np.random

    # Y 轴自适应
    all_max = max(input_values) * (1 + fluctuation_pct)
    step = 2 if all_max < 30 else (5 if all_max < 100 else 10)
    y_max_tick = int(np.ceil(all_max / step) * step)
    y_ticks = list(range(0, y_max_tick + 1, step))

    N = int(total_length_mm * points_per_mm)
    x = np.linspace(0, total_length_mm, N)

    all_curves = {}
    all_steady = {}
    meta_info = {}

    for g in range(num_groups):
        if seed is not None:
            rng = np.random.RandomState(seed + g)
        else:
            rng = np.random

        target = input_values[g]
        lo, hi = target * (1 - fluctuation_pct), target * (1 + fluctuation_pct)

        # --- 0~20mm 轻微锯齿爬升 ---
        n_rise = int(rise_end_mm * points_per_mm)
        x_rise = x[:n_rise]
        t = np.linspace(0, 1, n_rise)
        trend = target * (0.15 + 0.80 * t**1.5)
        noise = rng.uniform(-target * 0.02, target * 0.02, n_rise)
        y_rise = trend + noise
        y_rise = np.clip(y_rise, 0, target * 1.05)

        # --- 20~160mm 平稳段 ---
        n_steady = int((fall_start_mm - rise_end_mm) * points_per_mm)
        raw = rng.uniform(lo, hi, n_steady)
        y_steady = uniform_filter1d(raw, size=8)

        # --- 160~220mm 下坠段 ---
        n_fall = N - n_rise - n_steady
        x_fall = x[n_rise + n_steady:]

        has_peak = rng.random() < 0.5
        if has_peak:
            peak_at = int(n_fall * rng.uniform(0.05, 0.20))
            peak_val = target * rng.uniform(1.02, 1.08)
        else:
            peak_at = 0
            peak_val = target

        fall_begin = int(n_fall * rng.uniform(0.15, 0.50))
        fall_span = int(n_fall * rng.uniform(0.15, 0.45))
        if fall_begin + fall_span >= n_fall:
            fall_span = n_fall - fall_begin - 1

        y_fall = np.zeros(n_fall)

        pre_fall_len = fall_begin - peak_at
        if pre_fall_len > 0:
            y_fall[peak_at:fall_begin] = uniform_filter1d(
                rng.uniform(lo, hi, pre_fall_len), size=5
            )
        elif peak_at > 0:
            y_fall[peak_at] = peak_val

        fb = fall_begin
        fe = min(fall_begin + fall_span, n_fall)
        if fe > fb:
            t_f = np.linspace(0, 1, fe - fb)
            k = rng.uniform(5, 8)
            y_fall[fb:fe] = peak_val * (1 - (np.exp(k * t_f) - 1) / (np.exp(k) - 1))

        # 强制归零
        above = np.where(y_fall > 0.5)[0]
        if len(above) > 0:
            last = above[-1]
            y_fall[last + 3:] = 0.0

        # 拼接
        y_full = np.concatenate([y_rise, y_steady, y_fall])
        y_full = np.clip(y_full, 0, y_max_tick * 1.05)

        # 全局兜底归零
        above_all = np.where(y_full > 0.5)[0]
        if len(above_all) > 0:
            y_full[above_all[-1] + 3:] = 0.0

        name = f'曲线{g+1}'
        all_curves[name] = y_full
        all_steady[name] = y_full[n_rise:n_rise + n_steady]
        meta_info[name] = {'peak': has_peak}

    # --- 统计 ---
    rows = []
    for g, (name, y_s) in enumerate(all_steady.items()):
        rows.append({
            'No.': f'曲线{g+1}',
            '最大荷重(gf)': round(float(np.max(y_s)), 3),
            '最小荷重(gf)': round(float(np.min(y_s)), 3),
            '平均荷重(gf)': round(float(np.mean(y_s)), 3),
        })

    max_vals = [r['最大荷重(gf)'] for r in rows]
    min_vals = [r['最小荷重(gf)'] for r in rows]
    avg_vals = [r['平均荷重(gf)'] for r in rows]
    rows.append({'No.': '最大值', '最大荷重(gf)': round(max(max_vals), 3),
                '最小荷重(gf)': round(max(min_vals), 3),
                '平均荷重(gf)': round(max(avg_vals), 3)})
    rows.append({'No.': '最小值', '最大荷重(gf)': round(min(max_vals), 3),
                '最小荷重(gf)': round(min(min_vals), 3),
                '平均荷重(gf)': round(min(avg_vals), 3)})
    rows.append({'No.': '平均值', '最大荷重(gf)': round(np.mean(max_vals), 3),
                '最小荷重(gf)': round(np.mean(min_vals), 3),
                '平均荷重(gf)': round(np.mean(avg_vals), 3)})

    stats_df = pd.DataFrame(rows)

    # 逐点数据
    raw_df = pd.DataFrame({
        '变形(mm)': np.round(x, 2),
        **{f'曲线{k+1}': np.round(v, 3) for k, v in enumerate(all_curves.values())}
    })

    return x, all_curves, stats_df, raw_df, y_max_tick, step


# ============================================================
# 绘图函数
# ============================================================
def draw_figure(x, all_curves, stats_df, input_values, y_max_tick, step):
    """绘制曲线图 + 统计表格，返回 matplotlib figure"""

    num_groups = len(input_values)
    total_length_mm = 220.0
    fluctuation_pct = 0.20

    # --- 布局参数 ---
    _row_h = 0.032
    _n_rows = len(stats_df) + 1
    _tbl_total = _n_rows * _row_h
    _gap = _row_h * 1.0
    _bottom_margin = 0.02
    _tbl_bottom = _bottom_margin
    _tbl_top = _tbl_bottom + _tbl_total
    _curve_bottom = _tbl_top + _gap
    _top_margin = 0.03
    _left = 0.10
    _right = 0.95
    _curve_height = 1.0 - _top_margin - _curve_bottom

    fig_w_inch = 12
    fig_h_inch = 9.0

    fig = plt.figure(figsize=(fig_w_inch, fig_h_inch), dpi=150)
    fig.patch.set_facecolor('#e8e8e8')

    # --- 曲线图 ---
    ax = fig.add_axes([_left, _curve_bottom, _right - _left, _curve_height])
    ax.set_facecolor('#d8d8d8')
    ax.set_xlim(0, total_length_mm)
    ax.set_ylim(0, y_max_tick)

    y_ticks = list(range(0, y_max_tick + 1, step))
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([f"{int(v)}" for v in y_ticks], fontsize=9)
    ax.tick_params(axis='y', length=0, pad=8)

    x_ticks = list(range(0, int(total_length_mm) + 1, 10))
    ax.set_xticks(x_ticks)
    ax.tick_params(axis='x', length=3, labelsize=7.5)

    ax.yaxis.grid(True, linestyle=':', linewidth=0.4, alpha=0.5, color='#999')
    ax.xaxis.grid(True, linestyle=':', linewidth=0.3, alpha=0.3, color='#999')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for s in ['left', 'bottom']:
        ax.spines[s].set_linewidth(0.8)
        ax.spines[s].set_color('#666')

    # S15 / E15
    for _x in [40, 160]:
        line = Line2D([_x, _x], [0, y_max_tick],
                       color='#2196f3', linewidth=1.3, alpha=0.9,
                       dashes=(4, 3, 1, 3))
        ax.add_line(line)
    y_annot = y_max_tick - step * 0.12
    ax.text(40, y_annot, ' S15', fontsize=8.5, color='#1565c0', fontweight='bold')
    ax.text(160, y_annot, ' E15', fontsize=8.5, color='#1565c0', fontweight='bold')

    # 画曲线
    colors = ['#1a1a1a', '#c0392b', '#2980b9']
    for i, (name, y) in enumerate(all_curves.items()):
        ax.plot(x[:len(y)], y, color=colors[i % 3], linewidth=0.8,
                label=f'曲线{i+1} (输入 {input_values[i]:.0f})', zorder=3)

    # 峰值标注
    for i, (name, y) in enumerate(all_curves.items()):
        mask = (x >= 160) & (x <= 185)
        seg_y = y[mask]
        seg_x = x[mask]
        if len(seg_y) > 0:
            j = np.argmax(seg_y)
            px, py = seg_x[j], seg_y[j]
            ax.plot(px, py, 'o', color=colors[i % 3], markersize=3, zorder=6)
            ax.annotate(f'峰值 {py:.1f}@{px:.0f}', xy=(px, py),
                        xytext=(px + 3, py + step * 0.25), fontsize=6.5,
                        color=colors[i % 3], fontweight='bold')

    ax.legend(loc='upper left', fontsize=9, framealpha=0.92,
              edgecolor='#aaa', fancybox=True, borderpad=0.8)

    ax.set_xlabel('变形（mm）', fontsize=11, labelpad=8, color='#333')
    ax.set_ylabel('荷重（gf）', fontsize=11, labelpad=8, color='#333')

    title_str = (f'剥离试验曲线  |  波动 +/-{int(fluctuation_pct*100)}%  |  '
                 f'断崖坠落·自动归零')
    ax.set_title(title_str, fontsize=12, fontweight='bold', pad=12, color='#222')

    # --- 表格标题 ---
    fig.text((_left + _right) / 2, _tbl_top + _gap * 0.35,
             '统计结果（平稳段 40~160mm）',
             fontsize=10, fontweight='bold', ha='center', va='center', color='#222')

    # --- 表格 ---
    tbl_ax = fig.add_axes([_left, _tbl_bottom, _right - _left, _tbl_total])
    tbl_ax.axis('off')

    col_labels = ['No.', '最大荷重(gf)', '最小荷重(gf)', '平均荷重(gf)']
    table_rows = stats_df.values.tolist()
    col_w = [0.10, 0.27, 0.27, 0.36]
    col_w[-1] = 1.0 - sum(col_w[:-1])

    t = tbl_ax.table(
        cellText=table_rows,
        colLabels=col_labels,
        cellLoc='center',
        loc='center',
        colWidths=col_w,
    )
    t.auto_set_font_size(False)
    t.set_fontsize(8.5)
    t.scale(1.0, 1.5)

    for j in range(4):
        c = t[0, j]
        c.set_facecolor('#e0e0e0')
        c.set_text_props(fontweight='bold')
        c.set_edgecolor('#666')
        c.set_linewidth(0.7)

    for i in range(len(table_rows)):
        for j in range(4):
            c = t[i + 1, j]
            c.set_edgecolor('#999')
            c.set_linewidth(0.5)
            if i >= len(table_rows) - 3:
                c.set_facecolor('#f5f5f5')
                c.set_text_props(fontweight='bold')

    return fig


# ============================================================
# Streamlit UI
# ============================================================
def main():
    import streamlit as st

    st.set_page_config(
        page_title="剥离试验曲线生成器",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 剥离试验曲线生成器")
    st.caption("输入三条曲线的平稳段均值，自动生成带统计表格的曲线图")

    # --- 侧边栏参数 ---
    with st.sidebar:
        st.header("⚙️ 参数设置")

        st.subheader("曲线输入值")
        v1 = st.number_input("曲线1 输入值 (gf)", value=13.0, step=0.5, format="%.1f")
        v2 = st.number_input("曲线2 输入值 (gf)", value=15.0, step=0.5, format="%.1f")
        v3 = st.number_input("曲线3 输入值 (gf)", value=18.0, step=0.5, format="%.1f")

        st.subheader("高级参数")
        fluct = st.slider("波动范围 (%)", min_value=5, max_value=50, value=20, step=5) / 100.0
        seed_val = st.number_input("随机种子 (0=随机)", value=42, step=1)

        st.markdown("---")
        st.info(
            "**横坐标**: 0~220mm\n\n"
            "- 0~20: 锯齿爬升\n"
            "- 20~30: 分化→平稳\n"
            "- 40~160: 平稳波动\n"
            "- 160~220: 峰值→断崖坠落"
        )

    input_values = [v1, v2, v3]
    seed = int(seed_val) if seed_val > 0 else None

    # --- 生成数据 ---
    with st.spinner("正在生成曲线..."):
        x, all_curves, stats_df, raw_df, y_max_tick, step = generate_curves(
            input_values, fluctuation_pct=fluct, seed=seed
        )
        fig = draw_figure(x, all_curves, stats_df, input_values, y_max_tick, step)

    # --- 主区域 ---
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("曲线图 + 统计表")
        st.pyplot(fig, use_container_width=True)

    with col2:
        st.subheader("📋 统计汇总")
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

        st.subheader("📥 下载")
        # PNG
        buf_png = io.BytesIO()
        fig.savefig(buf_png, format='png', dpi=200)
        buf_png.seek(0)
        b64_png = base64.b64encode(buf_png.read()).decode()
        st.markdown(
            f'<a href="data:image/png;base64,{b64_png}" download="peel_curve.png">'
            f'📷 下载 PNG 图片</a>',
            unsafe_allow_html=True,
        )

        # Excel
        buf_xlsx = io.BytesIO()
        with pd.ExcelWriter(buf_xlsx, engine='openpyxl') as writer:
            raw_df.to_excel(writer, sheet_name='逐点数据', index=False)
            stats_df.to_excel(writer, sheet_name='统计汇总', index=False)
        buf_xlsx.seek(0)
        st.download_button(
            label="📊 下载 Excel 数据",
            data=buf_xlsx,
            file_name="peel_curve_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # --- 逐点数据展开 ---
    with st.expander("📂 查看逐点数据"):
        st.dataframe(raw_df, use_container_width=True, height=300)

    plt.close(fig)


if __name__ == '__main__':
    main()

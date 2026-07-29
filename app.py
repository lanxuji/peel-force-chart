import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64

# ------------------- 页面配置 -------------------
st.set_page_config(
    page_title="Peel Force Curve Generator",
    page_icon=":chart_with_upwards_trend:",
    layout="wide"
)

# ------------------- 全局样式 -------------------
BG_COLOR = "#f5fafd"       # 画布背景色（与原图一致）
GRID_COLOR = "#b3d9ff"     # 网格颜色（浅蓝）
TEXT_COLOR = "#333333"     # 文字颜色
ST15_LINE = "#666666"      # s15虚线颜色
E15_LINE = "#666666"       # e15虚线颜色
CURVE_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]  # 曲线颜色（与原图多曲线风格匹配）

# ------------------- 侧边栏参数配置 -------------------
with st.sidebar:
    st.header("Curve Parameters")
    num_curves = st.number_input(
        "Number of Curves", 
        min_value=1, 
        max_value=50, 
        value=3, 
        help="Maximum 50 curves (matches your requirement)"
    )
    
    # 每条曲线的参数（动态生成输入框）
    curve_params = []
    for i in range(num_curves):
        with st.expander(f"Curve {i+1} Settings"):
            mean = st.number_input(
                f"Mean (gf) - Curve {i+1}", 
                min_value=0.1, 
                max_value=100.0, 
                value=8.0 if i < 2 else 9.0,  # 前两条8，第三条9（匹配原图）
                step=0.1
            )
            deviation = st.slider(
                f"Deviation (%) - Curve {i+1}", 
                min_value=0, 
                max_value=50, 
                value=30,  # 原图偏差约±30%
                step=1
            )
            curve_params.append({"mean": mean, "deviation": deviation})

    # 有效区间（s15和e15）
    st.subheader("Valid Interval")
    valid_start = st.number_input("s15 (mm)", min_value=0.0, max_value=200.0, value=30.0, step=1.0)
    valid_end = st.number_input("e15 (mm)", min_value=0.0, max_value=200.0, value=160.0, step=1.0)

    # 生成按钮
    generate_btn = st.button("Generate Curves & Report", type="primary")


# ------------------- 曲线生成逻辑（完全匹配原图趋势） -------------------
def generate_curve(mean, deviation, valid_start, valid_end, x_max=220, y_max=20):
    """生成单条剥离力曲线（严格匹配原图：快速上升→平台波动→s15/e15→快速下降）"""
    x = np.linspace(0, x_max, 1000)  # 足够多的点保证平滑
    y = np.zeros_like(x)
    
    # 1. 阶段1：0~15mm，快速上升（斜率大）
    rise_phase = x <= 15
    y[rise_phase] = mean * (x[rise_phase] / 15) * (1 + np.random.normal(0, 0.05, sum(rise_phase)))  # 带小噪声
    
    # 2. 阶段2：15~valid_start，平稳过渡（斜率小）
    transition_phase = (x > 15) & (x <= valid_start)
    y[transition_phase] = mean * (1 + np.random.normal(0, 0.03, sum(transition_phase)))
    
    # 3. 阶段3：valid_start~valid_end，平台波动（均值mean，偏差deviation%）
    platform_phase = (x > valid_start) & (x <= valid_end)
    y[platform_phase] = mean * (1 + np.random.normal(0, deviation/100, sum(platform_phase)))
    
    # 4. 阶段4：valid_end~x_max，快速下降（斜率负）
    fall_phase = x > valid_end
    y[fall_phase] = mean * (1 - (x[fall_phase] - valid_end) / (x_max - valid_end)) * (1 + np.random.normal(0, 0.05, sum(fall_phase)))
    y[fall_phase] = np.clip(y[fall_phase], 0, None)  # 力不能为负
    
    return x, y


# ------------------- 主逻辑（生成+可视化+统计） -------------------
if generate_btn:
    st.session_state.curves = []  # 存储所有曲线数据
    
    with st.spinner("Generating curves..."):
        fig, ax = plt.subplots(figsize=(10, 6), dpi=150)  # 高DPI保证清晰度
        ax.set_facecolor(BG_COLOR)  # 画布背景色
        
        # 绘制每条曲线
        for i, params in enumerate(curve_params):
            mean = params["mean"]
            dev = params["deviation"]
            x, y = generate_curve(mean, dev, valid_start, valid_end)
            
            # 存储曲线数据（用于后续统计）
            curve_data = {
                "id": i+1,
                "x": x,
                "y": y,
                "mean": mean,
                "dev": dev,
                "max": np.max(y),
                "min": np.min(y),
                "avg": np.mean(y[(x >= valid_start) & (x <= valid_end)])  # 仅统计有效区间的平均
            }
            st.session_state.curves.append(curve_data)
            
            # 绘制曲线（配色与原图一致）
            ax.plot(x, y, color=CURVE_COLORS[i % len(CURVE_COLORS)], 
                    linewidth=1.2, label=f"Plot {i+1} (μ={mean}gf)")
        
        # 绘制s15和e15垂直虚线（匹配原图灰色虚线）
        ax.axvline(x=valid_start, color=ST15_LINE, linestyle=":", linewidth=1.2, label="s15")
        ax.axvline(x=valid_end, color=E15_LINE, linestyle=":", linewidth=1.2, label="e15")
        
        # 绘制s15和e15处的水平标记（小横线+文字）
        ax.annotate("s15", xy=(valid_start, y_max*0.95), xytext=(valid_start, y_max*0.98),
                    ha="center", va="bottom", color=ST15_LINE, fontsize=10)
        ax.annotate("e15", xy=(valid_end, y_max*0.95), xytext=(valid_end, y_max*0.98),
                    ha="center", va="bottom", color=E15_LINE, fontsize=10)
        
        # 网格样式（浅蓝虚线，与原图一致）
        ax.grid(True, color=GRID_COLOR, linestyle="--", alpha=0.7)
        
        # 轴标签与标题（中文，匹配原图）
        ax.set_xlabel("变形 (mm)", fontsize=12, color=TEXT_COLOR)
        ax.set_ylabel("剥离力 (gf)", fontsize=12, color=TEXT_COLOR)
        ax.set_title(f"批量剥离力测试曲线（共{num_curves}条）", fontsize=14, color=TEXT_COLOR)
        
        # 图例（右上角，小字体，透明背景）
        ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
        
        # 轴范围（匹配原图：x到220，y到20）
        ax.set_xlim(0, x_max)
        ax.set_ylim(0, y_max)
        
        # 刻度样式（与原图一致）
        ax.tick_params(axis="both", labelsize=10, color=TEXT_COLOR)
        
        # 紧凑布局（防止标签截断）
        plt.tight_layout()
        
        # 显示曲线
        st.subheader("📊 曲线预览")
        st.pyplot(fig)
        
        # ------------------- 统计表格（匹配原图格式） -------------------
        st.subheader("📋 测试数据统计")
        stats_df = pd.DataFrame({
            "曲线编号": [f"Plot {c['id']}" for c in st.session_state.curves],
            "目标均值(gf)": [c["mean"] for c in st.session_state.curves],
            "偏差(%)": [c["dev"] for c in st.session_state.curves],
            "实测最大(gf)": [round(c["max"], 3) for c in st.session_state.curves],
            "实测最小(gf)": [round(c["min"], 3) for c in st.session_state.curves],
            "有效区间平均(gf)": [round(c["avg"], 3) for c in st.session_state.curves]
        })
        st.dataframe(stats_df, use_container_width=True)
        
        # ------------------- 数据下载（PNG图片+CSV表格） -------------------
        st.subheader("📥 数据下载")
        col1, col2 = st.columns(2)
        
        # 1. 下载曲线图（PNG）
        with col1:
            img_buf = BytesIO()
            fig.savefig(img_buf, format="png", bbox_inches="tight", dpi=300)
            img_buf.seek(0)
            st.download_button(
                label="下载曲线图 (PNG)",
                data=img_buf,
                file_name="peel_force_curves.png",
                mime="image/png"
            )
        
        # 2. 下载统计数据（CSV）
        with col2:
            csv_buf = BytesIO()
            stats_df.to_csv(csv_buf, index=False, encoding="utf-8-sig")
            csv_buf.seek(0)
            st.download_button(
                label="下载统计数据 (CSV)",
                data=csv_buf,
                file_name="peel_force_stats.csv",
                mime="text/csv"
            )
        
        st.success(f"✅ 成功生成{num_curves}条曲线！")


# ------------------- 初始提示 -------------------
else:
    st.info("👈 请在左侧边栏设置曲线数量、均值、偏差、s15/e15区间，然后点击「生成曲线」按钮。")

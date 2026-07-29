import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from io import BytesIO

# ==================== 基础配置（避免字体/编码报错）====================
st.set_page_config(page_title="剥离力曲线生成器", layout="wide")
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False

# ==================== 剥离力测试固定参数（和你原软件完全一致）====================
CLIMB_END = 20          # 0-20mm爬升段
VALID_START = 40        # s15标记位置（x=40mm）
VALID_END = 160         # e15标记位置（x=160mm）
DROP_START = 170        # 170mm后下降段
BG_COLOR = "#e6f2ff"    # 浅蓝网格背景（原软件配色）
GRID_COLOR = "#b3d9ff"  # 网格线颜色
MAX_CURVES = 50         # 最大支持50条曲线（你之前的要求）

# ==================== 核心曲线生成函数（验证通过的版本）====================
def generate_peel_curve(mean: float, dev: float):
    """生成单条符合工业测试逻辑的剥离力曲线"""
    x = np.arange(0, 201)  # 横坐标0-200mm
    y = np.zeros_like(x, dtype=float)
    base_noise = np.random.normal(0, mean * 0.03, len(x))
    
    for i in range(len(x)):
        if i < CLIMB_END:
            # 0-20mm自然爬升
            y[i] = mean * 0.1 * np.exp(i / 8) + base_noise[i]
        elif i < VALID_START:
            # 20-40mm过渡段
            progress = (i - CLIMB_END) / (VALID_START - CLIMB_END)
            y[i] = mean * 0.8 + (mean - mean * 0.8) * progress + base_noise[i]
        elif i < VALID_END:
            # 40-160mm有效波动区（偏差±dev%）
            wave = mean * 0.08 * np.sin(i * 0.1)
            random_fluct = np.random.normal(0, mean * (dev/100) * 0.5)
            y[i] = mean + wave + random_fluct + base_noise[i]
        elif i < DROP_START:
            # 160-170mm预下降过渡
            progress = (i - VALID_END) / (DROP_START - VALID_END)
            y[i] = y[VALID_END] * (1 - 0.2 * progress) + base_noise[i]
        else:
            # 170mm后平滑下降
            y[i] = max(0, y[DROP_START] * np.exp(-(i - DROP_START) / 20) + base_noise[i])
    y[y < 0] = 0
    return x, y

# ==================== 侧边栏：参数输入（支持最多50条）====================
with st.sidebar:
    st.header("⚙️ 曲线参数设置")
    st.caption(f"当前支持最多{MAX_CURVES}条曲线批量生成")
    
    # 曲线数量控制
    num_curves = st.number_input("曲线数量", min_value=1, max_value=MAX_CURVES, value=3)
    
    # 预填你之前要的8/8/9默认值
    default_means = [8.0, 8.0, 9.0] + [5.0] * (MAX_CURVES - 3)
    default_devs = [30.0] * MAX_CURVES
    
    # 动态生成每条曲线的输入项
    curve_params = []
    for i in range(num_curves):
        with st.expander(f"曲线 {i+1} 配置"):
            mean = st.number_input(f"目标均值(gf)", min_value=0.1, value=default_means[i], step=0.1, key=f"mean_{i}")
            dev = st.slider(f"偏差(%)", min_value=5, max_value=50, value=int(default_devs[i]), step=5, key=f"dev_{i}")
            curve_params.append({"mean": mean, "dev": dev})
    
    # 生成按钮
    generate_btn = st.button("🚀 生成曲线", type="primary", use_container_width=True)

# ==================== 主界面：结果展示 ====================
st.title("📈 剥离力测试曲线生成器")
st.caption("匹配工业剥离力测试软件标准 | 支持最多50条曲线批量生成")

if generate_btn:
    with st.spinner(f"正在生成{num_curves}条曲线..."):
        # 生成所有曲线
        curves_data = []
        for i, param in enumerate(curve_params):
            x, y = generate_peel_curve(param["mean"], param["dev"])
            curves_data.append({
                "id": i+1, "x": x, "y": y,
                "max": round(np.max(y), 3), "min": round(np.min(y), 3), "avg": round(np.mean(y[y>0]), 3)
            })
        
        # 绘制曲线（带s15/e15标记）
        fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
        colors = plt.cm.tab20.colors  # 多曲线配色，适配50条输入
        for i, curve in enumerate(curves_data):
            ax.plot(curve["x"], curve["y"], color=colors[i%len(colors)], linewidth=1.2, label=f"Plot {curve['id']}")
        
        # 添加s15/e15灰色虚线标记
        ax.axvline(x=VALID_START, color="#666666", linestyle=":", linewidth=1.2, label="s15")
        ax.axvline(x=VALID_END, color="#666666", linestyle=":", linewidth=1.2, label="e15")
        
        # 样式匹配原软件
        ax.set_facecolor(BG_COLOR)
        ax.grid(True, color=GRID_COLOR, linestyle="--", alpha=0.7)
        ax.set_xlabel("变形 (mm)")
        ax.set_ylabel("剥离力 (gf)")
        ax.set_title(f"剥离力测试曲线（共{num_curves}条）")
        ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
        plt.tight_layout()
        
        # 显示曲线
        st.subheader("📊 曲线预览")
        st.pyplot(fig)
        
        # 统计表格
        st.subheader("📋 测试数据统计")
        stats_df = pd.DataFrame({
            "曲线编号": [f"Plot {c['id']}" for c in curves_data],
            "目标均值(gf)": [c["mean"] for c in curves_data],
            "实测最大(gf)": [c["max"] for c in curves_data],
            "实测最小(gf)": [c["min"] for c in curves_data],
            "实测平均(gf)": [c["avg"] for c in curves_data]
        })
        st.dataframe(stats_df, use_container_width=True)
        
        # 下载功能
        st.subheader("📥 数据下载")
        col1, col2 = st.columns(2)
        with col1:
            img_buf = BytesIO()
            fig.savefig(img_buf, format="png", bbox_inches="tight", dpi=300)
            img_buf.seek(0)
            st.download_button("下载曲线图(PNG)", img_buf, "peel_force_curves.png", "image/png")
        with col2:
            csv_buf = BytesIO()
            stats_df.to_csv(csv_buf, index=False, encoding="utf-8-sig")
            csv_buf.seek(0)
            st.download_button("下载统计数据(CSV)", csv_buf, "peel_force_stats.csv", "text/csv")
        
        st.success(f"✅ 成功生成{num_curves}条曲线！")
else:
    st.info("请在左侧边栏设置曲线数量、均值、偏差，点击「生成曲线」按钮开始。默认已预填3条曲线（均值8/8/9，偏差30%）")

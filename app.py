import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from io import BytesIO

# ==================== 基础配置 ====================
st.set_page_config(
    page_title="剥离力曲线批量生成器",
    page_icon="📊",
    layout="wide"
)

# 初始化session_state，存储曲线数量和参数（默认3条，预填8/8/9）
if "num_curves" not in st.session_state:
    st.session_state.num_curves = 3
if "curve_params" not in st.session_state:
    st.session_state.curve_params = [
        {"mean": 8.0, "dev": 30.0, "mode": "smooth", "end": 200},
        {"mean": 8.0, "dev": 30.0, "mode": "smooth", "end": 200},
        {"mean": 9.0, "dev": 30.0, "mode": "smooth", "end": 200}
    ]

# Matplotlib配置，避免字体报错
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False

# 剥离力测试固定参数（和你之前确认的一致）
CLIMB_END = 20          # 爬升段结束（0-20mm）
VALID_START = 40        # s15标记位置（x=40mm）
VALID_END = 160         # e15标记位置（x=160mm）
DROP_START = 170        # 下降段起始（170mm后）
BG_COLOR = "#e6f2ff"    # 浅蓝网格背景，匹配原软件
GRID_COLOR = "#b3d9ff"  # 网格线颜色

# ==================== 核心曲线生成函数 ====================
def generate_single_curve(mean: float, dev: float, mode: str, end: int):
    """生成单条符合工业测试逻辑的剥离力曲线"""
    x = np.arange(0, end + 1, 1)
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
            # 170mm后下降段（支持3种模式）
            if mode == "smooth":
                y[i] = max(0, y[DROP_START] * np.exp(-(i - DROP_START) / 20) + base_noise[i])
            elif mode == "peak":
                peak = y[DROP_START] * 1.1 if np.random.rand() > 0.5 else y[DROP_START]
                y[i] = max(0, peak * np.exp(-(i - DROP_START) / 25) + base_noise[i])
            else:  # cut模式，直接截断到0
                y[i] = 0
    y[y < 0] = 0
    return x, y

# ==================== 侧边栏：参数输入 ====================
with st.sidebar:
    st.header("⚙️ 批量曲线参数")
    st.caption(f"当前曲线数量：{st.session_state.num_curves}/50")
    
    # 添加/删除曲线按钮（最多50条）
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ 添加曲线", disabled=st.session_state.num_curves >= 50):
            st.session_state.num_curves += 1
            st.session_state.curve_params.append({
                "mean": 5.0, "dev": 30.0, "mode": "smooth", "end": 200
            })
    with col2:
        if st.button("➖ 删除曲线", disabled=st.session_state.num_curves <= 1):
            st.session_state.num_curves -= 1
            st.session_state.curve_params.pop()
    
    st.divider()
    
    # 动态生成每条曲线的输入项
    new_params = []
    for i in range(st.session_state.num_curves):
        st.subheader(f"曲线 {i+1}")
        param = st.session_state.curve_params[i]
        
        mean = st.number_input(f"目标均值(gf)", min_value=0.1, value=param["mean"], step=0.1, key=f"mean_{i}")
        dev = st.slider(f"偏差(%)", min_value=5, max_value=50, value=int(param["dev"]), step=5, key=f"dev_{i}")
        mode = st.selectbox(f"下降模式", options=["smooth", "peak", "cut"], index=["smooth", "peak", "cut"].index(param["mode"]), key=f"mode_{i}")
        end = st.number_input(f"终结位置(mm)", min_value=180, max_value=220, value=param["end"], step=10, key=f"end_{i}")
        
        new_params.append({"mean": mean, "dev": float(dev), "mode": mode, "end": end})
        st.divider()
    
    st.session_state.curve_params = new_params
    generate_btn = st.button("🚀 批量生成曲线", type="primary", use_container_width=True)

# ==================== 主界面：结果展示 ====================
st.title("📈 剥离力曲线批量生成工具")
st.caption("支持最多50条曲线批量生成，匹配工业剥离力测试软件标准")

if generate_btn:
    with st.spinner(f"正在生成{st.session_state.num_curves}条曲线..."):
        # 生成所有曲线
        curves_data = []
        for i, param in enumerate(st.session_state.curve_params):
            x, y = generate_single_curve(param["mean"], param["dev"], param["mode"], param["end"])
            curves_data.append({
                "id": i+1, "x": x, "y": y, "mean": param["mean"], "dev": param["dev"],
                "mode": param["mode"], "end": param["end"],
                "max": round(np.max(y), 3), "min": round(np.min(y), 3), "avg": round(np.mean(y[y>0]), 3)
            })
        
        # 绘制曲线图（带s15/e15标记）
        fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
        colors = plt.cm.tab20.colors
        for i, curve in enumerate(curves_data):
            ax.plot(curve["x"], curve["y"], color=colors[i%len(colors)], linewidth=1.2, label=f"Plot {curve['id']} (μ={curve['mean']}gf)")
        ax.axvline(x=VALID_START, color="#666666", linestyle=":", linewidth=1.2, label="s15")
        ax.axvline(x=VALID_END, color="#666666", linestyle=":", linewidth=1.2, label="e15")
        
        # 样式匹配原软件
        ax.set_facecolor(BG_COLOR)
        ax.grid(True, color=GRID_COLOR, linestyle="--", alpha=0.7)
        ax.set_xlabel("变形 (mm)")
        ax.set_ylabel("剥离力 (gf)")
        ax.set_title(f"批量剥离力测试曲线（共{len(curves_data)}条）")
        ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
        plt.tight_layout()
        
        # 显示结果
        st.subheader("📊 曲线预览")
        st.pyplot(fig)
        
        # 统计表格
        st.subheader("📋 测试数据统计")
        single_stats = pd.DataFrame({
            "曲线编号": [f"Plot {c['id']}" for c in curves_data],
            "目标均值(gf)": [c["mean"] for c in curves_data],
            "偏差(%)": [c["dev"] for c in curves_data],
            "下降模式": [c["mode"] for c in curves_data],
            "实测最大(gf)": [c["max"] for c in curves_data],
            "实测最小(gf)": [c["min"] for c in curves_data],
            "实测平均(gf)": [c["avg"] for c in curves_data]
        })
        st.dataframe(single_stats, use_container_width=True)
        
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
            single_stats.to_csv(csv_buf, index=False, encoding="utf-8-sig")
            csv_buf.seek(0)
            st.download_button("下载统计数据(CSV)", csv_buf, "peel_force_stats.csv", "text/csv")
        
        st.success(f"✅ 成功生成{st.session_state.num_curves}条曲线！")
else:
    st.info("请在左侧边栏调整参数，点击「批量生成曲线」按钮开始生成。默认已预填3条曲线（均值8/8/9，偏差30%）")

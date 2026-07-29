import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ==================== 全局配置（和你最初确认的一致）====================
plt.rcParams["font.family"] = "DejaVu Sans"  # 避免字体报错
plt.rcParams["axes.unicode_minus"] = False

# 曲线参数（固定符合你的要求）
X_TOTAL = 200          # 总横坐标长度
CLIMB_END = 20         # 0-20mm爬升段
VALID_START = 40       # s15标记位置（x=40）
VALID_END = 160        # e15标记位置（x=160）
DROP_START = 170       # 170mm后下降段
BG_COLOR = "#e6f2ff"   # 浅蓝网格背景（和原软件一致）
DEV_RANGE = 0.3        # 波动±30%

# ==================== 核心曲线生成函数（最初验证通过的版本）====================
def generate_peel_curve(base_mean):
    x = np.arange(0, X_TOTAL + 1)
    y = np.zeros_like(x, dtype=float)
    
    # 1. 0-20mm自然爬升
    climb_mask = x <= CLIMB_END
    y[climb_mask] = base_mean * 0.1 * np.exp(x[climb_mask] / 8)
    
    # 2. 20-40mm过渡段
    trans_mask = (x > CLIMB_END) & (x < VALID_START)
    y[trans_mask] = base_mean * (0.8 + 0.2 * (x[trans_mask] - CLIMB_END) / (VALID_START - CLIMB_END))
    
    # 3. 40-160mm有效波动区（带真实测试抖动）
    valid_mask = (x >= VALID_START) & (x <= VALID_END)
    valid_len = np.sum(valid_mask)
    base_valid = base_mean * (1 + np.random.uniform(-DEV_RANGE, DEV_RANGE))
    noise = np.random.normal(0, base_mean * 0.05, valid_len)
    periodic = base_mean * 0.1 * np.sin(2 * np.pi * x[valid_mask] / 30)
    y[valid_mask] = base_valid + noise + periodic
    
    # 4. 160-170mm预下降过渡
    pre_drop_mask = (x > VALID_END) & (x < DROP_START)
    y[pre_drop_mask] = y[VALID_END] * (1 - 0.2 * (x[pre_drop_mask] - VALID_END) / (DROP_START - VALID_END))
    
    # 5. 170-200mm指数下降
    drop_mask = x >= DROP_START
    y[drop_mask] = y[DROP_START] * np.exp(-(x[drop_mask] - DROP_START) / 20)
    y[y < 0] = 0  # 避免负值
    
    return x, y

# ==================== Streamlit界面（最精简稳定版）====================
st.set_page_config(page_title="Peel Force Tester", layout="wide")
st.title("剥离力测试曲线生成器")
st.caption("复刻工业剥离力测试软件风格 | 默认输入：8/8/9")

# 侧边栏参数（默认填好你要的8、8、9）
with st.sidebar:
    st.header("测试参数")
    mean1 = st.number_input("曲线1均值(gf)", value=8.0, step=0.1)
    mean2 = st.number_input("曲线2均值(gf)", value=8.0, step=0.1)
    mean3 = st.number_input("曲线3均值(gf)", value=9.0, step=0.1)
    dev = st.slider("波动范围(%)", 10, 50, 30, step=5)
    generate_btn = st.button("生成曲线", type="primary")

# 主界面
if generate_btn:
    with st.spinner("生成曲线中..."):
        # 生成三条曲线
        input_means = [mean1, mean2, mean3]
        curves = []
        for i, mean in enumerate(input_means):
            x, y = generate_peel_curve(mean)
            curves.append({
                "id": i+1,
                "x": x,
                "y": y,
                "max": np.max(y),
                "min": np.min(y),
                "avg": np.mean(y[y>0])
            })
        
        # 绘制曲线
        fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
        
        for i, curve in enumerate(curves):
            ax.plot(curve["x"], curve["y"], color=colors[i], linewidth=1.5, 
                    label=f"Plot {curve['id']} (μ={curve['mean']})")
        
        # 添加s15/e15标记
        ax.axvline(x=VALID_START, color="#666666", linestyle=":", linewidth=1.2, label="s15")
        ax.axvline(x=VALID_END, color="#666666", linestyle=":", linewidth=1.2, label="e15")
        
        # 样式设置（和原软件一致）
        ax.set_facecolor(BG_COLOR)
        ax.grid(True, color="#b3d9ff", linestyle="--", alpha=0.7)
        ax.set_xlabel("变形 (mm)")
        ax.set_ylabel("剥离力 (gf)")
        ax.set_title("剥离力测试曲线")
        ax.legend(loc="upper right", fontsize=9)
        plt.tight_layout()
        
        # 显示曲线
        st.pyplot(fig)
        
        # 显示统计表格
        st.subheader("测试数据统计")
        stats_df = pd.DataFrame({
            "编号": [f"Plot {c['id']}" for c in curves] + ["整体平均", "整体最大", "整体最小"],
            "目标均值(gf)": [c["mean"] for c in curves] + ["-", "-", "-"],
            "实测最大(gf)": [round(c["max"], 3) for c in curves] + [
                round(np.mean([c["max"] for c in curves]), 3),
                round(np.max([c["max"] for c in curves]), 3),
                round(np.min([c["max"] for c in curves]), 3)
            ],
            "实测最小(gf)": [round(c["min"], 3) for c in curves] + [
                round(np.mean([c["min"] for c in curves]), 3),
                round(np.max([c["min"] for c in curves]), 3),
                round(np.min([c["min"] for c in curves]), 3)
            ],
            "实测平均(gf)": [round(c["avg"], 3) for c in curves] + [
                round(np.mean([c["avg"] for c in curves]), 3),
                round(np.max([c["avg"] for c in curves]), 3),
                round(np.min([c["avg"] for c in curves]), 3)
            ]
        })
        st.dataframe(stats_df, use_container_width=True)
else:
    st.info("点击左侧「生成曲线」按钮，即可生成默认8/8/9的三条测试曲线")

# ==================== 运行入口 ====================
if __name__ == "__main__":
    st.runtime.legacy_caching.clear_cache()

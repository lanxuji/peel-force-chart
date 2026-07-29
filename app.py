# app.py - Full English Version for Peel Force Analysis
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.drawing.image import Image as ExcelImage
from io import BytesIO

# ==================== Global Config ====================
# Fix matplotlib font issue (no Chinese characters used)
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False

# Test parameters (fixed per your requirements)
CLIMB_END = 20          # Initial climb phase ends at 20mm
VALID_START = 40        # Valid test zone starts at 40mm (s15 marker)
VALID_END = 160         # Valid test zone ends at 160mm (e15 marker)
DROP_START = 170        # Drop phase starts at 170mm
MAX_DISPLACEMENT = 200  # Total displacement range 0-200mm
DEFAULT_DEVIATION = 0.3 # ±30% fluctuation range
BG_COLOR = "#e6f2ff"    # Light blue grid background (matches original software)

# ==================== Core Curve Generation ====================
def generate_single_curve(target_mean: float, deviation: float = DEFAULT_DEVIATION) -> tuple:
    """
    Generate a single peel force curve matching real test logic
    Args:
        target_mean: Target average peel force (gf)
        deviation: Allowed fluctuation range (0-1 ratio)
    Returns:
        x: Displacement array (mm)
        y: Peel force array (gf)
    """
    x = np.arange(0, MAX_DISPLACEMENT + 1)
    y = np.zeros_like(x, dtype=float)
    base_noise = np.random.normal(0, target_mean * 0.05, len(x))
    
    for i in range(len(x)):
        if i < CLIMB_END:
            # Phase 1: Natural climb from 0 to ~80% of target mean
            y[i] = target_mean * 0.8 * (i / CLIMB_END) + base_noise[i]
        elif i < VALID_START:
            # Phase 2: Smooth transition to valid test zone
            progress = (i - CLIMB_END) / (VALID_START - CLIMB_END)
            y[i] = target_mean * 0.8 + (target_mean - target_mean * 0.8) * progress + base_noise[i]
        elif i < VALID_END:
            # Phase 3: Valid test zone with realistic fluctuations
            wave = target_mean * 0.1 * np.sin(i * 0.1)  # Small periodic variation
            random_fluct = np.random.normal(0, target_mean * deviation * 0.5)
            y[i] = target_mean + wave + random_fluct + base_noise[i]
        elif i < DROP_START:
            # Phase 4: Pre-drop transition
            progress = (i - VALID_END) / (DROP_START - VALID_END)
            y[i] = y[VALID_END] * (1 - 0.2 * progress) + base_noise[i]
        else:
            # Phase 5: Exponential drop to 0
            y[i] = max(0, y[DROP_START] * np.exp(-(i - DROP_START) / 20) + base_noise[i])
    
    return x, y

# ==================== Excel Report Generator ====================
def create_excel_report(curves_data: list) -> BytesIO:
    """
    Generate Excel report with embedded chart and statistics table
    Args:
        curves_data: List of dicts containing curve metadata
    Returns:
        BytesIO buffer containing the Excel file
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Peel Test Report"
    
    # -------------------- Top Section: Test Metadata --------------------
    metadata = [
        ["Company", "Dongguan Yuda New Materials Co., Ltd."],
        ["Report Title", "Peel Strength Test Report"],
        ["Customer Name", "Jishunlong"],
        ["Test Standard", "GB2792-2014 Adhesive Tape Peel Strength Test Method"],
        ["Test Speed", "300.000 mm/min"],
        ["Test Date", "2024-08-05 10:14:49"],
        ["", ""]  # Empty row for spacing
    ]
    
    for row_idx, (key, value) in enumerate(metadata, start=1):
        cell_key = ws.cell(row=row_idx, column=1, value=key)
        cell_val = ws.cell(row=row_idx, column=2, value=value)
        # Style metadata rows
        cell_key.font = Font(bold=True, size=10)
        cell_key.alignment = Alignment(horizontal="left", vertical="center")
        cell_val.font = Font(size=10)
        cell_val.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[row_idx].height = 18
    
    # -------------------- Middle Section: Embedded Chart --------------------
    # Generate chart image first
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    
    for idx, curve in enumerate(curves_data):
        ax.plot(curve["x"], curve["y"], color=colors[idx], linewidth=1.5, 
                label=f"Plot {idx+1} (μ={curve['mean']}gf)")
    
    # Add s15/e15 markers
    ax.axvline(x=VALID_START, color="gray", linestyle=":", linewidth=1.2, alpha=0.7)
    ax.axvline(x=VALID_END, color="gray", linestyle=":", linewidth=1.2, alpha=0.7)
    ax.text(VALID_START, ax.get_ylim()[1]*0.95, "s15", ha="center", va="top", fontsize=9)
    ax.text(VALID_END, ax.get_ylim()[1]*0.95, "e15", ha="center", va="top", fontsize=9)
    
    # Chart styling
    ax.set_xlabel("Displacement (mm)")
    ax.set_ylabel("Peel Force (gf)")
    ax.set_title("Peel Force Test Curves")
    ax.grid(True, color="white", linestyle="-", linewidth=0.8, alpha=0.8)
    ax.set_facecolor(BG_COLOR)
    ax.legend(fontsize=8)
    plt.tight_layout()
    
    # Save chart to buffer and embed in Excel
    img_buf = BytesIO()
    plt.savefig(img_buf, format="png", bbox_inches="tight")
    plt.close(fig)
    img_buf.seek(0)
    
    # Insert chart into Excel (starting at row 9, column 1)
    img = ExcelImage(img_buf)
    img.width = 650
    img.height = 300
    ws.add_image(img, "A9")
    ws.row_dimensions[9].height = 220  # Adjust row height for chart
    
    # -------------------- Bottom Section: Statistics Table --------------------
    # Table headers
    table_start_row = 22
    headers = ["No.", "Target Mean (gf)", "Max Peel Force (gf)", 
               "Min Peel Force (gf)", "Avg Peel Force (gf)"]
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=table_start_row, column=col_idx, value=header)
        cell.font = Font(bold=True, size=10)
        cell.fill = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[chr(64 + col_idx)].width = 18
    
    # Fill curve data
    for idx, curve in enumerate(curves_data):
        row = table_start_row + 1 + idx
        ws.cell(row=row, column=1, value=f"Plot {idx+1}")
        ws.cell(row=row, column=2, value=curve["mean"])
        ws.cell(row=row, column=3, value=round(curve["max"], 3))
        ws.cell(row=row, column=4, value=round(curve["min"], 3))
        ws.cell(row=row, column=5, value=round(curve["avg"], 3))
        # Style data rows
        for col in range(1, 6):
            ws.cell(row=row, column=col).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=row, column=col).font = Font(size=10)
    
    # Add summary rows (Overall Max/Avg)
    summary_start = table_start_row + len(curves_data) + 1
    ws.cell(row=summary_start, column=1, value="Overall Max").font = Font(bold=True, size=10)
    ws.cell(row=summary_start, column=1).alignment = Alignment(horizontal="center")
    ws.cell(row=summary_start, column=3, value=round(max(c["max"] for c in curves_data), 3)).alignment = Alignment(horizontal="center")
    ws.cell(row=summary_start, column=4, value=round(max(c["min"] for c in curves_data), 3)).alignment = Alignment(horizontal="center")
    ws.cell(row=summary_start, column=5, value=round(max(c["avg"] for c in curves_data), 3)).alignment = Alignment(horizontal="center")
    
    ws.cell(row=summary_start+1, column=1, value="Overall Avg").font = Font(bold=True, size=10)
    ws.cell(row=summary_start+1, column=1).alignment = Alignment(horizontal="center")
    ws.cell(row=summary_start+1, column=3, value=round(np.mean([c["max"] for c in curves_data]), 3)).alignment = Alignment(horizontal="center")
    ws.cell(row=summary_start+1, column=4, value=round(np.mean([c["min"] for c in curves_data]), 3)).alignment = Alignment(horizontal="center")
    ws.cell(row=summary_start+1, column=5, value=round(np.mean([c["avg"] for c in curves_data]), 3)).alignment = Alignment(horizontal="center")
    
    # Save to buffer
    excel_buf = BytesIO()
    wb.save(excel_buf)
    excel_buf.seek(0)
    return excel_buf

# ==================== Streamlit UI ====================
def main():
    st.set_page_config(page_title="Peel Force Analyzer", layout="wide")
    st.title("📊 Peel Force Test Data Generator")
    st.caption("Generate simulated peel force curves matching industrial test standards")
    
    # Sidebar controls
    with st.sidebar:
        st.header("Input Parameters")
        st.info("Default values pre-filled with your requested data: 8, 8, 9")
        
        # Input fields for 3 curves (pre-filled with 8,8,9)
        mean1 = st.number_input("Curve 1 Mean (gf)", value=8.0, step=0.1)
        mean2 = st.number_input("Curve 2 Mean (gf)", value=8.0, step=0.1)
        mean3 = st.number_input("Curve 3 Mean (gf)", value=9.0, step=0.1)
        
        deviation = st.slider("Fluctuation Range (%)", min_value=10, max_value=50, value=30, step=5)
        generate_btn = st.button("🚀 Generate Curves & Report", type="primary")
    
    # Main content area
    if generate_btn:
        with st.spinner("Generating curves and Excel report..."):
            # Generate 3 curves with input means
            input_means = [mean1, mean2, mean3]
            curves_data = []
            
            for mean in input_means:
                x, y = generate_single_curve(mean, deviation/100)
                curves_data.append({
                    "x": x,
                    "y": y,
                    "mean": mean,
                    "max": np.max(y),
                    "min": np.min(y),
                    "avg": np.mean(y[y>0])  # Exclude initial 0 values from average
                })
            
            # Display curves
            st.subheader("Generated Peel Force Curves")
            fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
            colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
            
            for idx, curve in enumerate(curves_data):
                ax.plot(curve["x"], curve["y"], color=colors[idx], linewidth=1.5,
                        label=f"Plot {idx+1} (μ={curve['mean']}gf)")
            
            # Add s15/e15 markers
            ax.axvline(x=VALID_START, color="gray", linestyle=":", linewidth=1.2, alpha=0.7)
            ax.axvline(x=VALID_END, color="gray", linestyle=":", linewidth=1.2, alpha=0.7)
            ax.text(VALID_START, ax.get_ylim()[1]*0.95, "s15", ha="center", va="top", fontsize=10)
            ax.text(VALID_END, ax.get_ylim()[1]*0.95, "e15", ha="center", va="top", fontsize=10)
            
            # Chart styling
            ax.set_xlabel("Displacement (mm)")
            ax.set_ylabel("Peel Force (gf)")
            ax.set_title("Peel Force Test Curves")
            ax.grid(True, color="white", linestyle="-", linewidth=0.8, alpha=0.8)
            ax.set_facecolor(BG_COLOR)
            ax.legend(fontsize=9)
            st.pyplot(fig)
            
            # Display statistics table
            st.subheader("Test Statistics")
            stats_df = pd.DataFrame({
                "No.": [f"Plot {i+1}" for i in range(len(curves_data))],
                "Target Mean (gf)": [c["mean"] for c in curves_data],
                "Max Peel Force (gf)": [round(c["max"], 3) for c in curves_data],
                "Min Peel Force (gf)": [round(c["min"], 3) for c in curves_data],
                "Avg Peel Force (gf)": [round(c["avg"], 3) for c in curves_data]
            })
            st.dataframe(stats_df, use_container_width=True)
            
            # Download Excel report button
            excel_buf = create_excel_report(curves_data)
            st.download_button(
                label="📥 Download Full Excel Report",
                data=excel_buf,
                file_name="peel_force_test_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            st.success("Generation complete! Click the download button above to save the Excel report.")
    else:
        st.info("Adjust parameters in the sidebar and click 'Generate Curves & Report' to start.")

if __name__ == "__main__":
    main()

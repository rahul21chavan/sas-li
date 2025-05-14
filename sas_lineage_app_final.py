
import streamlit as st
import re
import pandas as pd
import os
from io import BytesIO
import graphviz
from pathlib import Path
from fpdf import FPDF
import tempfile

# --- SAS Parser Logic ---
def parse_sas_file(file_content, filename):
    lineage = []
    current_target = None

    for line in file_content.splitlines():
        line = line.strip().lower()
        if line.startswith("data "):
            match = re.match(r"data\s+(\w+)", line)
            if match:
                current_target = match.group(1)
        elif line.startswith("set ") or line.startswith("merge "):
            sources = re.findall(r"\b\w+\b", line.split(" ", 1)[1])
            for src in sources:
                lineage.append({
                    "target": current_target,
                    "source": src,
                    "source_file": "",
                    "sas_file": filename
                })
        elif "infile" in line:
            match = re.search(r'infile\s+[\'"]([^\'"]+)[\'"]', line)
            if match:
                lineage.append({
                    "target": current_target,
                    "source": "",
                    "source_file": match.group(1),
                    "sas_file": filename
                })

    return lineage

def walk_directory_for_sas_files(folder):
    folder_path = Path(folder)
    return list(folder_path.rglob("*.sas"))

def dataframe_to_pdf(df):
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 12)
            self.cell(0, 10, "SAS Lineage Report", 0, 1, "C")

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    col_widths = [40, 40, 60, 40]
    headers = ["Target", "Source", "Source File", "SAS File"]
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, 1)
    pdf.ln()

    for _, row in df.iterrows():
        pdf.cell(col_widths[0], 10, str(row["target"]), 1)
        pdf.cell(col_widths[1], 10, str(row["source"]), 1)
        pdf.cell(col_widths[2], 10, str(row["source_file"]), 1)
        pdf.cell(col_widths[3], 10, str(row["sas_file"]), 1)
        pdf.ln()

    output = BytesIO()
    pdf.output(output)
    return output

# --- Streamlit App Interface ---
st.set_page_config(page_title="SAS Lineage Extractor", layout="wide")
st.title("📊 SAS Deep Lineage Extractor")

mode = st.radio("Choose input mode", ["Upload Files", "Directory Scan"])

sas_files = []

if mode == "Upload Files":
    uploaded_files = st.file_uploader("Upload SAS files", type="sas", accept_multiple_files=True)
    if uploaded_files:
        for file in uploaded_files:
            sas_files.append((file.name, file.read().decode("utf-8", errors="ignore")))
else:
    folder = st.text_input("Enter path to directory containing .sas files", "")
    if folder and Path(folder).exists():
        discovered_files = walk_directory_for_sas_files(folder)
        for file_path in discovered_files:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                sas_files.append((str(file_path.name), f.read()))

enable_graph = st.checkbox("Show dependency graph", value=True)

if sas_files:
    full_lineage = []
    for fname, content in sas_files:
        lineage = parse_sas_file(content, fname)
        full_lineage.extend(lineage)

    df = pd.DataFrame(full_lineage)

    if not df.empty:
        st.subheader("🔍 Extracted Lineage")
        st.dataframe(df)

        # Excel output
        excel_output = BytesIO()
        with pd.ExcelWriter(excel_output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Lineage")
        st.download_button("📥 Download Excel", excel_output.getvalue(), file_name="lineage_output.xlsx", mime="application/vnd.ms-excel")

        # PDF output
        pdf_data = dataframe_to_pdf(df)
        st.download_button("📄 Download PDF", data=pdf_data.getvalue(), file_name="lineage_report.pdf", mime="application/pdf")

        # Dependency Graph
        if enable_graph:
            st.subheader("📈 Lineage Dependency Graph")
            dot = graphviz.Digraph()

            for _, row in df.iterrows():
                target = row["target"]
                source = row["source"]
                source_file = row["source_file"]

                if source:
                    dot.edge(source, target, color="blue")
                if source_file:
                    dot.edge(source_file, target, color="green")

            st.graphviz_chart(dot)
    else:
        st.warning("No lineage data found.")

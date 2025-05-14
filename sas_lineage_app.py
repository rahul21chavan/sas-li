
import streamlit as st
import re
import pandas as pd
import os
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
            sources = re.findall(r"\w+", line.split(" ", 1)[1])
            for src in sources:
                lineage.append({
                    "target": current_target,
                    "source": src,
                    "source_file": "",
                    "sas_file": filename
                })
        elif "infile" in line:
            match = re.search(r'infile\s+['"]([^'"]+)['"]', line)
            if match:
                lineage.append({
                    "target": current_target,
                    "source": "",
                    "source_file": match.group(1),
                    "sas_file": filename
                })

    return lineage

# --- Streamlit App Interface ---
st.set_page_config(page_title="SAS Lineage Extractor", layout="wide")
st.title("📊 SAS Deep Lineage Extractor")

uploaded_files = st.file_uploader("Upload one or more SAS files", type="sas", accept_multiple_files=True)

if uploaded_files:
    full_lineage = []

    for file in uploaded_files:
        content = file.read().decode("utf-8", errors="ignore")
        lineage = parse_sas_file(content, file.name)
        full_lineage.extend(lineage)

    df = pd.DataFrame(full_lineage)

    if not df.empty:
        st.subheader("🔍 Extracted Lineage")
        st.dataframe(df)

        # Download link
        csv = df.to_csv(index=False)
        st.download_button("📥 Download CSV", csv, file_name="lineage_output.csv", mime="text/csv")
    else:
        st.info("No lineage data found in the provided SAS files.")

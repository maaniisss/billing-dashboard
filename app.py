import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
from datetime import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Jigri Billing Dashboard", page_icon="💰", layout="wide")

# --- TITLE & STYLE ---
st.title("💰 Smart Billing Dashboard")
st.markdown("### Upload Bills -> Extract Data -> Download Excel")
st.divider()

# --- SIDEBAR (Settings) ---
with st.sidebar:
    st.header("📂 Purana Data (Optional)")
    existing_file = st.file_uploader("Agar purani Excel hai to yahan dalein:", type=["xlsx"])
    st.info("Tip: Nayi PDF upload karo, system automatic data nikal kar Excel bana dega.")

# --- MAIN LOGIC ---
uploaded_pdfs = st.file_uploader("📄 Nayi Bill PDFs yahan dalein (Multiple select kar sakte hain)", 
                                 type=["pdf"], accept_multiple_files=True)

if uploaded_pdfs:
    if st.button(f"🚀 Process {len(uploaded_pdfs)} Bills"):
        
        all_data = []
        progress_bar = st.progress(0)
        
        for index, pdf_file in enumerate(uploaded_pdfs):
            try:
                # PDF Padhna
                with pdfplumber.open(pdf_file) as pdf:
                    full_text = ""
                    for page in pdf.pages:
                        full_text += page.extract_text() + "\n"
                
                # --- DATA EXTRACTION (Wahi purana logic) ---
                lines = full_text.split('\n')
                vr_no = "Not Found"
                date = "Not Found"
                party_name = "Not Found"
                amount = 0.0
                code_head = "Not Found"

                for line in lines:
                    # VR No & Date
                    if "V.R. no." in line.lower():
                        parts = line.split("Date")
                        vr_part = parts[0]
                        if "." in vr_part:
                            vr_no = vr_part.split(".")[-1].strip()
                        if len(parts) > 1:
                            date = parts[1].replace(":", "").strip()

                    # Amount
                    if "Passed for payment of Rs." in line:
                        try:
                            amt_part = line.split("Rs.")[1].strip()
                            amt_clean = amt_part.split()[0].replace(",", "")
                            amount = float(amt_clean)
                        except:
                            pass

                    # Party Name
                    if "Name of Party" in line:
                        party_name = line.split("Party")[1].replace(":", "").strip()

                    # Code Head
                    if "Code No." in line:
                        code_head = line.split("Code No.")[1].replace(":", "").strip()

                # Add to List
                all_data.append({
                    "Date": date,
                    "VR_No": vr_no,
                    "Party_Name": party_name,
                    "Code_Head": code_head,
                    "Amount": amount,
                    "File_Name": pdf_file.name,
                    "Status": "Pending"
                })
                
            except Exception as e:
                st.error(f"Error in {pdf_file.name}: {e}")
            
            # Progress Bar Update
            progress_bar.progress((index + 1) / len(uploaded_pdfs))

        # --- DATAFRAME CREATION ---
        new_df = pd.DataFrame(all_data)
        
        # Agar purani file di hai, to merge karo
        if existing_file:
            old_df = pd.read_excel(existing_file)
            final_df = pd.concat([old_df, new_df], ignore_index=True)
            st.success("✅ Purana Data + Naya Data Merge ho gaya!")
        else:
            final_df = new_df
            st.success("✅ Naya Data Extract ho gaya!")

        # --- SHOW DATA ---
        st.subheader("📊 Extracted Data")
        st.dataframe(final_df, use_container_width=True)

        # --- DOWNLOAD BUTTON ---
        # Excel ko memory mein save karna
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False)
            
        st.download_button(
            label="📥 Download Updated Excel",
            data=buffer.getvalue(),
            file_name=f"Billing_Data_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

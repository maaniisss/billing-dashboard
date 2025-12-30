import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
from datetime import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Billing Dashboard", page_icon="💰", layout="wide")
st.title("💰 Billing Dashboard (Final Fixed)")

# --- SESSION STATE (Data Safe Rakhne ke liye) ---
if 'final_df' not in st.session_state:
    st.session_state.final_df = pd.DataFrame()

# --- 1. SIDEBAR (FILTERS - AB HAMESHA DIKHENGE) ---
with st.sidebar:
    st.header("🔍 Search & Filters")
    
    # Empty lists initially
    all_vrs = []
    all_codes = []
    all_parties = []
    
    # Agar Data hai, toh list update karo
    if not st.session_state.final_df.empty:
        df = st.session_state.final_df
        # Sort karke list banao taaki dhoondna aasaan ho
        if 'VR_No' in df.columns: 
            all_vrs = sorted(df['VR_No'].astype(str).unique().tolist())
        if 'Code_Head' in df.columns: 
            all_codes = sorted(df['Code_Head'].astype(str).unique().tolist())
        if 'Party_Name' in df.columns: 
            all_parties = sorted(df['Party_Name'].astype(str).unique().tolist())

    # --- YE RAHE AAPKE SEARCH BOXES ---
    search_vr = st.multiselect("🔢 VR No. Search", all_vrs, placeholder="Type VR No...")
    search_code = st.multiselect("🏷️ Code Head Search", all_codes, placeholder="Type Code Head...")
    search_party = st.multiselect("👤 Party Search", all_parties, placeholder="Type Name...")
    
    st.divider()
    st.write("Controls:")
    # Upload Old Data
    existing_file = st.file_uploader("📂 Purani Excel File", type=["xlsx"])
    if st.button("🗑️ Clear All Data"):
        st.session_state.final_df = pd.DataFrame()
        st.rerun()

# --- 2. MAIN PROCESS ---
uploaded_pdfs = st.file_uploader("📄 Naye Bills Upload Karein", type=["pdf"], accept_multiple_files=True)

if uploaded_pdfs:
    if st.button(f"🚀 Process {len(uploaded_pdfs)} Bills"):
        
        all_data = []
        progress_bar = st.progress(0)
        
        for index, pdf_file in enumerate(uploaded_pdfs):
            try:
                with pdfplumber.open(pdf_file) as pdf:
                    full_text = ""
                    for page in pdf.pages:
                        full_text += page.extract_text() + "\n"
                
                # --- EXTRACTION LOGIC ---
                
                # 1. VR Number
                vr_match = re.search(r"(VR No\.|DV No\.:|VR No)\s*(\d+)", full_text)
                vr_no = vr_match.group(2) if vr_match else ""

                # 2. Code Head (Strict Format: 93/020/91)
                code_matches = re.findall(r"\d{2}/\d{3}/\d{2}", full_text)
                if code_matches:
                    code_head = code_matches[0] # Pehla match
                else:
                    # Fallback for Salary Bills
                    sec_match = re.search(r"Section:\s*(\d+)", full_text)
                    code_head = sec_match.group(1) if sec_match else ""

                # 3. Date
                date_match = re.search(r"Date:[-]?\s*(\d{2}-\d{2}-\d{4})", full_text)
                date = date_match.group(1) if date_match else ""

                # 4. Amount
                amt_match = re.search(r"(Total of above Rs|DV Total:|Total Amount)\s*(\d+)", full_text)
                amount = float(amt_match.group(2)) if amt_match else 0.0

                # 5. Party Name (IFSC Logic)
                ifsc_matches = re.findall(r'[A-Z]{4}0[A-Z0-9]{6}', full_text)
                unique_ifsc = len(set(ifsc_matches))
                
                party_name = ""
                if unique_ifsc > 1:
                    party_name = "Salary/Group Payment"
                else:
                    lines = full_text.split('\n')
                    for i, line in enumerate(lines):
                        if any(c in line for c in ifsc_matches) or "SBIN" in line:
                            if i + 1 < len(lines):
                                clean_name = lines[i+1].strip()
                                if not clean_name.isdigit() and len(clean_name) > 2:
                                    party_name = clean_name
                                    break
                
                if not party_name and "Remarks" in full_text: party_name = "Vendor (Check Name)"

                # Add to list
                all_data.append({
                    "Date": date,
                    "VR_No": vr_no,
                    "Code_Head": code_head,
                    "Party_Name": party_name,
                    "Amount": amount,
                    "Paid": False,
                    "File_Name": pdf_file.name
                })

            except:
                pass # Error ignore karo taaki ruke nahi
            
            progress_bar.progress((index + 1) / len(uploaded_pdfs))

        # Data Jodna
        new_df = pd.DataFrame(all_data)
        
        if existing_file:
            try:
                old_df = pd.read_excel(existing_file)
                st.session_state.final_df = pd.concat([old_df, new_df], ignore_index=True)
            except:
                st.session_state.final_df = new_df
        else:
            if not st.session_state.final_df.empty:
                 st.session_state.final_df = pd.concat([st.session_state.final_df, new_df], ignore_index=True)
            else:
                 st.session_state.final_df = new_df
        
        st.rerun()

# --- 3. SHOW TABLE & DOWNLOAD ---

if not st.session_state.final_df.empty:
    df_display = st.session_state.final_df.copy()

    # Apply Filters
    if search_vr:
        df_display = df_display[df_display['VR_No'].isin(search_vr)]
    if search_code:
        df_display = df_display[df_display['Code_Head'].isin(search_code)]
    if search_party:
        df_display = df_display[df_display['Party_Name'].isin(search_party)]

    st.subheader("📊 Data Table")
    
    # EDITABLE TABLE
    edited_df = st.data_editor(
        df_display,
        column_config={
            "Paid": st.column_config.CheckboxColumn("Done?", width="small"),
            "VR_No": st.column_config.TextColumn("VR No"),
            "Code_Head": st.column_config.TextColumn("Code Head"),
            "Party_Name": st.column_config.TextColumn("Party Name", width="large"),
            "Amount": st.column_config.NumberColumn("Amount", format="₹ %d"),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )

    # Totals
    paid_val = edited_df[edited_df['Paid']==True]['Amount'].sum()
    total_val = edited_df['Amount'].sum()
    
    c1, c2 = st.columns(2)
    c1.metric("Total Amount", f"₹ {total_val:,.0f}")
    c2.metric("Paid Amount", f"₹ {paid_val:,.0f}")

    # Download
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        edited_df.to_excel(writer, index=False)
    st.download_button("📥 Download Excel", buffer.getvalue(), "Billing_Data.xlsx")

else:
    st.info("👈 Left side se purani Excel upload karein, ya upar se nayi PDF daalein.")

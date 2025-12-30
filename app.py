import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
from datetime import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Billing Dashboard", page_icon="💰", layout="wide")
st.title("💰 Billing Dashboard (Colab Style Logic)")

# --- SESSION STATE ---
if 'final_df' not in st.session_state:
    st.session_state.final_df = pd.DataFrame()

# --- SIDEBAR (FILTERS) ---
with st.sidebar:
    st.header("🔍 Search Filters")
    
    # Empty lists
    all_vrs = []
    all_parties = []
    all_codes = [] 
    
    if not st.session_state.final_df.empty:
        df = st.session_state.final_df
        if 'VR_No' in df.columns: 
            all_vrs = sorted(df['VR_No'].astype(str).unique().tolist())
        if 'Party_Name' in df.columns: 
            all_parties = sorted(df['Party_Name'].astype(str).unique().tolist())
        
        # Code extraction for filter list
        if 'Code_Head_Details' in df.columns:
            unique_codes = set()
            for detail_str in df['Code_Head_Details'].astype(str):
                # Detail format: "93/020/91 (138357), 01/460/01 (123952)"
                codes = re.findall(r"\d{2}/\d{3}/\d{2}", detail_str)
                unique_codes.update(codes)
            all_codes = sorted(list(unique_codes))

    search_vr = st.multiselect("🔢 VR No.", all_vrs)
    search_code = st.multiselect("🏷️ Code Head", all_codes)
    search_party = st.multiselect("👤 Party Name", all_parties)
    
    st.divider()
    existing_file = st.file_uploader("📂 Purani Excel File", type=["xlsx"])
    if st.button("🗑️ Clear All Data"):
        st.session_state.final_df = pd.DataFrame()
        st.rerun()

# --- MAIN PROCESS ---
uploaded_pdfs = st.file_uploader("📄 Bills Upload Karein", type=["pdf"], accept_multiple_files=True)

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
                
                # --- COLAB LOGIC (Line-by-Line Parsing) ---
                
                lines = full_text.split('\n')
                
                # Variables
                vr_no = ""
                date = ""
                party_name = ""
                total_amount = 0.0
                
                # List to store Code+Amount pairs found in this file
                code_breakdown = [] 

                # 1. First Pass: Text Logic (VR, Date, Party)
                vr_match = re.search(r"(VR No\.|DV No\.:|VR No)\s*(\d+)", full_text)
                vr_no = vr_match.group(2) if vr_match else ""

                date_match = re.search(r"Date:[-]?\s*(\d{2}-\d{2}-\d{4})", full_text)
                date = date_match.group(1) if date_match else ""

                amt_match = re.search(r"(Total of above Rs|DV Total:|Total Amount)\s*(\d+)", full_text)
                total_amount = float(amt_match.group(2)) if amt_match else 0.0
                
                # Party Name Logic (IFSC)
                ifsc_matches = re.findall(r'[A-Z]{4}0[A-Z0-9]{6}', full_text)
                unique_ifsc = len(set(ifsc_matches))
                if unique_ifsc > 1:
                    party_name = "Salary/Group Payment"
                else:
                    for i, line in enumerate(lines):
                        if any(c in line for c in ifsc_matches) or "SBIN" in line:
                            if i + 1 < len(lines):
                                clean_name = lines[i+1].strip()
                                if not clean_name.isdigit() and len(clean_name) > 2:
                                    party_name = clean_name
                                    break
                if not party_name and "Remarks" in full_text: party_name = "Vendor (Check Name)"

                # 2. Second Pass: THE COLAB LOOP (For Codes & Amounts)
                # Hum har line ko padhenge, agar Code Head mila to amount uthayenge
                
                for line in lines:
                    # Regex to find pattern xx/xxx/xx in the line
                    code_match = re.search(r"(\d{2}/\d{3}/\d{2})", line)
                    
                    if code_match:
                        code_found = code_match.group(1)
                        
                        # Ab usi line mein number dhoondo (Amount)
                        # Line example: "93/020/91 138357 0"
                        # Hum words split karenge
                        parts = line.split()
                        
                        found_amount = "0"
                        for part in parts:
                            # Code khud number na ban jaye, aur comma hata kar check karo
                            clean_part = part.replace(",", "")
                            if clean_part.isdigit() and part != code_found:
                                # Pehla bada number usually amount hota hai
                                if float(clean_part) > 0:
                                    found_amount = clean_part
                                    break
                        
                        # Pair bana kar list mein daal do
                        code_breakdown.append(f"{code_found} ({found_amount})")

                # Join all pairs: "93/020/91 (138357), 01/460/01 (123952)"
                code_details_str = ", ".join(code_breakdown) if code_breakdown else "No Code Found"

                all_data.append({
                    "Date": date,
                    "VR_No": vr_no,
                    "Code_Head_Details": code_details_str, # ✅ Colab Style Output
                    "Party_Name": party_name,
                    "Total_Amount": total_amount,
                    "Paid": False,
                    "File_Name": pdf_file.name
                })

            except:
                pass
            progress_bar.progress((index + 1) / len(uploaded_pdfs))

        new_df = pd.DataFrame(all_data)
        
        # Merge
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

# --- SHOW TABLE ---
if not st.session_state.final_df.empty:
    df_display = st.session_state.final_df.copy()

    # Filters
    if search_vr:
        df_display = df_display[df_display['VR_No'].isin(search_vr)]
    if search_party:
        df_display = df_display[df_display['Party_Name'].isin(search_party)]
    if search_code:
        # Search inside the logic string
        df_display = df_display[df_display['Code_Head_Details'].apply(
            lambda x: any(code in str(x) for code in search_code)
        )]

    st.subheader("📊 Live Billing Register")
    
    edited_df = st.data_editor(
        df_display,
        column_config={
            "Paid": st.column_config.CheckboxColumn("Done?", width="small"),
            "Code_Head_Details": st.column_config.TextColumn("Code Heads (Amount)", width="large"),
            "Total_Amount": st.column_config.NumberColumn("Total Bill", format="₹ %d"),
            "Party_Name": st.column_config.TextColumn("Party", width="medium"),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )

    # Download
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        edited_df.to_excel(writer, index=False)
    st.download_button("📥 Download Excel", buffer.getvalue(), "Billing_Register.xlsx")

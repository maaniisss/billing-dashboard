import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
from datetime import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Jigri Final Dashboard", page_icon="🏆", layout="wide")
st.title("🏆 Jigri Final Mission Dashboard (100% Accurate)")
st.markdown("### Logic: Colab Coordinate System + Smart Party Detection")
st.divider()

# --- SESSION STATE ---
if 'final_df' not in st.session_state:
    st.session_state.final_df = pd.DataFrame()

# --- 1. SIDEBAR (FILTERS) ---
with st.sidebar:
    st.header("🔍 Search Filters")
    
    # Empty lists
    all_vrs = []
    all_parties = []
    all_codes = []
    
    # Agar Data hai, to filter list update karo
    if not st.session_state.final_df.empty:
        df = st.session_state.final_df
        if 'VR_No' in df.columns: 
            all_vrs = sorted(df['VR_No'].astype(str).unique().tolist())
        if 'Party_Name' in df.columns: 
            all_parties = sorted(df['Party_Name'].astype(str).unique().tolist())
        if 'Code_Head' in df.columns: 
            all_codes = sorted(df['Code_Head'].astype(str).unique().tolist())

    # Search Boxes
    search_vr = st.multiselect("🔢 VR No.", all_vrs)
    search_code = st.multiselect("🏷️ Code Head", all_codes)
    search_party = st.multiselect("👤 Party Name", all_parties)
    
    # Type Filter (Receipt vs Charge)
    search_type = st.radio("Entry Type:", ["All", "Receipt", "Charge"], horizontal=True)
    
    st.divider()
    existing_file = st.file_uploader("📂 Purani Excel File", type=["xlsx"])
    if st.button("🗑️ Clear All Data"):
        st.session_state.final_df = pd.DataFrame()
        st.rerun()

# --- 2. MAIN PROCESS (COLAB LOGIC ADAPTED) ---
uploaded_pdfs = st.file_uploader("📄 Bills Upload Karein", type=["pdf"], accept_multiple_files=True)

# Regex for Code Head (xx/xxx/xx)
code_pattern = re.compile(r"(\d{2}/\d{3}/\d{2})")

if uploaded_pdfs:
    if st.button(f"🚀 Process {len(uploaded_pdfs)} Files"):
        
        all_entries = []
        progress_bar = st.progress(0)
        
        for index, pdf_file in enumerate(uploaded_pdfs):
            try:
                with pdfplumber.open(pdf_file) as pdf:
                    page = pdf.pages[0]
                    width = page.width
                    mid_point = width / 2 # Page ka aadha hissa
                    
                    # 1. TEXT EXTRACTION (For VR, Date, Party)
                    text = page.extract_text()
                    lines = text.split('\n')
                    
                    party_name = "Unknown"
                    vr_no = "0000"
                    pm_date = "Unknown"
                    
                    # Line by Line Scan (Text Logic)
                    for i, line in enumerate(lines):
                        # VR No
                        if "VR No" in line:
                            vr_match = re.search(r"VR No.*?(\d+)", line)
                            if vr_match: 
                                # Format nicely (e.g., 58 -> 0058)
                                vr_no = f"{int(vr_match.group(1)):04d}"
                        
                        # Date
                        if "Date:-" in line:
                            date_match = re.search(r"(\d{2}-\d{2}-\d{4})", line)
                            if date_match: pm_date = date_match.group(1)
                            
                        # --- PARTY NAME LOGIC (The Golden Rule: DV No - 2) ---
                        if "DV No.:" in line:
                            if i >= 2:
                                found_name = lines[i-2].strip()
                                # Thodi safai (agar galti se kuch number aa jaye)
                                if len(found_name) > 3: 
                                    party_name = found_name
                                else:
                                    # Fallback: Agar upar wali line khaali thi, to 3 line upar dekho
                                    if i >= 3: party_name = lines[i-3].strip()

                    # Month-Year Logic
                    month_year = "Unknown"
                    if pm_date != "Unknown":
                        try:
                            month_year = datetime.strptime(pm_date, "%d-%m-%Y").strftime("%Y-%m")
                        except: pass

                    # 2. CODE & AMOUNT EXTRACTION (The Coordinate Logic)
                    words = page.extract_words()
                    i = 0
                    while i < len(words):
                        word = words[i]
                        word_text = word['text']
                        
                        # Agar Code Head Pattern match ho (93/020/91)
                        if code_pattern.match(word_text):
                            code_head = word_text
                            
                            # Coordinate Check (Left vs Right)
                            x_pos = word['x0']
                            entry_type = "Receipt" if x_pos < mid_point else "Charge"
                            
                            # Next word Amount hona chahiye
                            amount = 0
                            if i + 1 < len(words):
                                next_word = words[i+1]
                                amt_text = next_word['text'].replace(",", "").strip()
                                if amt_text.isdigit():
                                    amount = float(amt_text)
                            
                            # Sirf valid amount add karo
                            if amount > 0:
                                all_entries.append({
                                    "Date": pm_date,
                                    "Month_Year": month_year,
                                    "VR_No": vr_no,
                                    "Party_Name": party_name,
                                    "Type": entry_type, # Receipt / Charge
                                    "Code_Head": code_head,
                                    "Amount": amount,
                                    "File_Name": pdf_file.name
                                })
                        i += 1
                        
            except Exception as e:
                st.error(f"Error in {pdf_file.name}: {e}")
            
            progress_bar.progress((index + 1) / len(uploaded_pdfs))

        # --- DATA SAVE LOGIC ---
        new_df = pd.DataFrame(all_entries)
        
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
        
        st.success("✅ Mission Accomplished! Data Processed.")
        st.rerun()

# --- 3. DISPLAY TABLE ---
if not st.session_state.final_df.empty:
    df_display = st.session_state.final_df.copy()

    # Apply Filters
    if search_vr:
        df_display = df_display[df_display['VR_No'].isin(search_vr)]
    if search_party:
        df_display = df_display[df_display['Party_Name'].isin(search_party)]
    if search_code:
        df_display = df_display[df_display['Code_Head'].isin(search_code)]
    if search_type != "All":
        df_display = df_display[df_display['Type'] == search_type]

    st.subheader("📊 Detailed Register")
    
    edited_df = st.data_editor(
        df_display,
        column_config={
            "Amount": st.column_config.NumberColumn("Amount", format="₹ %d"),
            "Type": st.column_config.TextColumn("R/C", width="small"),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )
    
    # Totals
    total_val = edited_df['Amount'].sum()
    receipt_val = edited_df[edited_df['Type'] == "Receipt"]['Amount'].sum()
    charge_val = edited_df[edited_df['Type'] == "Charge"]['Amount'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Net Total", f"₹ {total_val:,.0f}")
    c2.metric("📥 Total Receipts", f"₹ {receipt_val:,.0f}")
    c3.metric("📤 Total Charges", f"₹ {charge_val:,.0f}")

    # Download
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        edited_df.to_excel(writer, index=False)
    st.download_button("📥 Download Final Excel", buffer.getvalue(), "Jigri_Mission_Data.xlsx")

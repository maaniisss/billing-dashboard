import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
from datetime import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Jigri Billing Dashboard", page_icon="💰", layout="wide")

st.title("💰 Smart Billing Dashboard")
st.markdown("### 📂 Upload -> 🔍 Code Head Search -> ⚡ Track")
st.divider()

# --- INITIALIZE SESSION STATE ---
if 'final_df' not in st.session_state:
    st.session_state.final_df = pd.DataFrame()

# --- 1. SIDEBAR (SEARCH & FILTERS) ---
with st.sidebar:
    st.header("⚙️ Controls")
    
    # Upload Purana Data
    existing_file = st.file_uploader("📂 Purani Excel File", type=["xlsx"])
    st.divider()
    
    # --- SMART SEARCH FILTERS ---
    st.subheader("🔍 Search Filters")
    
    # Lists for dropdowns (Dynamic)
    opt_codes = []
    opt_vendors = []
    opt_months = []
    
    if not st.session_state.final_df.empty:
        df = st.session_state.final_df
        if 'Code_Head' in df.columns: 
            opt_codes = sorted(df['Code_Head'].astype(str).unique().tolist())
        if 'Party_Name' in df.columns: 
            opt_vendors = sorted(df['Party_Name'].astype(str).unique().tolist())
        if 'Month' in df.columns:
            opt_months = df['Month'].unique().tolist()

    # 1. CODE HEAD SEARCH (Sabse Zaroori)
    filter_code = st.multiselect("🏷️ Code Head (Type to Search)", opt_codes)
    
    # 2. Other Filters
    filter_vendor = st.multiselect("👤 Party Name", opt_vendors)
    filter_month = st.multiselect("📅 Month", opt_months)
    filter_status = st.radio("Show Status:", ["All", "Paid (Done)", "Unpaid (Pending)"], index=0)

# --- 2. MAIN LOGIC ---
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
                
                # --- EXTRACTION ---
                
                # A. VR Number
                vr_match = re.search(r"(VR No\.|DV No\.:|VR No)\s*(\d+)", full_text)
                vr_no = vr_match.group(2) if vr_match else "Unknown"

                # B. Date
                date_match = re.search(r"Date:[-]?\s*(\d{2}-\d{2}-\d{4})", full_text)
                date = date_match.group(1) if date_match else "Unknown"
                
                month_val = "Unknown"
                if date != "Unknown":
                    try:
                        month_val = datetime.strptime(date, "%d-%m-%Y").strftime("%B %Y")
                    except: pass

                # C. CODE HEAD (Major Change Here)
                # Logic: Sabse pehle XX/XXX/XX dhoondo (e.g. 93/020/91)
                code_head = "Unknown"
                
                # Regex for pattern like 93/020/91
                codes_found = re.findall(r"\d{2}/\d{3}/\d{2}", full_text)
                
                if codes_found:
                    # Pehla code utha lo (Main Head)
                    code_head = codes_found[0]
                else:
                    # Fallback: Agar slash wala nahi mila to 'Section' dhoondo
                    sec_match = re.search(r"Section:\s*(\d+)", full_text)
                    if sec_match:
                        code_head = sec_match.group(1)

                # D. Amount
                amt_match = re.search(r"(Total of above Rs|DV Total:|Total Amount)\s*(\d+)", full_text)
                amount = float(amt_match.group(2)) if amt_match else 0.0

                # E. Party Name
                ifsc_matches = re.findall(r'[A-Z]{4}0[A-Z0-9]{6}', full_text)
                unique_ifsc = len(set(ifsc_matches))
                
                party_name = "Unknown"
                if unique_ifsc > 1:
                    party_name = "Salary/Group Payment"
                else:
                    lines = full_text.split('\n')
                    found = False
                    for i, line in enumerate(lines):
                        if any(code in line for code in ifsc_matches) or "SBIN" in line:
                            if i + 1 < len(lines):
                                potential_name = lines[i+1].strip()
                                if not potential_name.isdigit() and len(potential_name) > 2:
                                    party_name = potential_name
                                    found = True
                                    break
                    if not found and "Remarks" in full_text:
                         party_name = "Vendor (Name Check)"

                all_data.append({
                    "Date": date,
                    "VR_No": vr_no,
                    "Code_Head": code_head, # Column Position 3
                    "Party_Name": party_name,
                    "Amount": amount,
                    "Month": month_val,
                    "Paid": False,
                    "File_Name": pdf_file.name
                })
            except Exception as e:
                st.error(f"Error in {pdf_file.name}: {e}")
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

# --- 3. DISPLAY ---
if not st.session_state.final_df.empty:
    df_display = st.session_state.final_df.copy()

    # Filters Apply
    if filter_code:
        df_display = df_display[df_display['Code_Head'].isin(filter_code)]
    if filter_vendor:
        df_display = df_display[df_display['Party_Name'].isin(filter_vendor)]
    if filter_month:
        df_display = df_display[df_display['Month'].isin(filter_month)]
    if filter_status == "Paid (Done)":
        df_display = df_display[df_display['Paid'] == True]
    elif filter_status == "Unpaid (Pending)":
        df_display = df_display[df_display['Paid'] == False]

    # Re-order columns for better view
    cols_order = ["Paid", "Date", "VR_No", "Code_Head", "Party_Name", "Amount", "File_Name"]
    # Only use columns that exist
    final_cols = [c for c in cols_order if c in df_display.columns]
    
    st.subheader("📊 Live Register")
    
    edited_df = st.data_editor(
        df_display[final_cols],
        column_config={
            "Paid": st.column_config.CheckboxColumn("Done?", default=False, width="small"),
            "Code_Head": st.column_config.TextColumn("Code Head", width="medium"),
            "Amount": st.column_config.NumberColumn("Amount", format="₹ %d"),
            "Party_Name": st.column_config.TextColumn("Party Name", width="large"),
        },
        disabled=["Date", "VR_No", "Code_Head", "File_Name"],
        hide_index=True,
        num_rows="dynamic",
        use_container_width=True
    )

    # Totals
    total = edited_df['Amount'].sum()
    paid = edited_df[edited_df['Paid'] == True]['Amount'].sum()
    
    c1, c2 = st.columns(2)
    c1.metric("💰 Total Amount", f"₹ {total:,.0f}")
    c2.metric("✅ Paid Amount", f"₹ {paid:,.0f}")

    # Download
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        edited_df.to_excel(writer, index=False)
    st.download_button("📥 Download Excel", buffer.getvalue(), f"Billing_{datetime.now().strftime('%d%m%Y')}.xlsx")

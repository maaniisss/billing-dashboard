import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
from datetime import datetime

# --- PAGE SETUP (Wide Mode) ---
st.set_page_config(page_title="Jigri Billing Dashboard", page_icon="💰", layout="wide")

st.title("💰 Smart Billing Dashboard")
st.markdown("### 📂 Upload -> 🔍 Auto-Detect -> ⚡ Filter & Track")
st.divider()

# --- 1. SIDEBAR (FILTERS & SETTINGS) ---
with st.sidebar:
    st.header("⚙️ Dashboard Controls")
    
    # Upload Purana Data
    existing_file = st.file_uploader("📂 Purani Excel File Jodein", type=["xlsx"])
    st.divider()
    
    # Filters (Ye tab dikhenge jab data hoga)
    st.subheader("🔍 Search & Filter")
    filter_month = st.multiselect("📅 Select Month", [])
    filter_vendor = st.multiselect("👤 Select Party/Vendor", [])
    filter_vr = st.multiselect("🔢 Select VR No.", [])
    filter_status = st.radio("Show Status:", ["All", "Paid (Done)", "Unpaid (Pending)"], index=0)

# --- 2. MAIN LOGIC (Processing) ---
uploaded_pdfs = st.file_uploader("📄 Naye Bills Upload Karein (Vendor ya Salary)", 
                                 type=["pdf"], accept_multiple_files=True)

# Data Store karne ke liye session state (Taaki refresh hone par data na bhaage)
if 'final_df' not in st.session_state:
    st.session_state.final_df = pd.DataFrame()

if uploaded_pdfs:
    if st.button(f"🚀 Process {len(uploaded_pdfs)} Bills"):
        
        all_data = []
        progress_bar = st.progress(0)
        
        for index, pdf_file in enumerate(uploaded_pdfs):
            try:
                # PDF Read
                with pdfplumber.open(pdf_file) as pdf:
                    full_text = ""
                    for page in pdf.pages:
                        full_text += page.extract_text() + "\n"
                
                # --- EXTRACTION LOGIC ---
                
                # A. VR Number
                vr_match = re.search(r"(VR No\.|DV No\.:|VR No)\s*(\d+)", full_text)
                vr_no = vr_match.group(2) if vr_match else "Unknown"

                # B. Date & Month
                date_match = re.search(r"Date:[-]?\s*(\d{2}-\d{2}-\d{4})", full_text)
                date = date_match.group(1) if date_match else "Unknown"
                
                # Month nikalna (Filter ke liye)
                month_val = "Unknown"
                if date != "Unknown":
                    try:
                        dt_obj = datetime.strptime(date, "%d-%m-%Y")
                        month_val = dt_obj.strftime("%B %Y") # e.g. December 2025
                    except:
                        pass

                # C. Code Head / Section
                # Pattern: "Section: 260900" ya Classification code "93/020/91"
                code_match = re.search(r"Section:\s*(\d+)", full_text)
                code_head = code_match.group(1) if code_match else ""
                
                # Agar Section nahi mila, to classification dhoondo
                if not code_head:
                    class_match = re.search(r"\d{2}/\d{3}/\d{2}", full_text)
                    code_head = class_match.group(0) if class_match else "General"

                # D. Amount
                amt_match = re.search(r"(Total of above Rs|DV Total:|Total Amount)\s*(\d+)", full_text)
                amount = float(amt_match.group(2)) if amt_match else 0.0

                # E. PARTY NAME (Smart Logic)
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

                # Add to List
                all_data.append({
                    "Date": date,
                    "Month": month_val,
                    "VR_No": vr_no,
                    "Code_Head": code_head,
                    "Party_Name": party_name,
                    "Amount": amount,
                    "Paid": False,  # Checkbox ke liye (False = Unticked)
                    "File_Name": pdf_file.name
                })
                
            except Exception as e:
                st.error(f"Error in {pdf_file.name}: {e}")
            
            progress_bar.progress((index + 1) / len(uploaded_pdfs))

        # Create DataFrame
        new_df = pd.DataFrame(all_data)
        
        # Merge with Existing
        if existing_file:
            try:
                old_df = pd.read_excel(existing_file)
                st.session_state.final_df = pd.concat([old_df, new_df], ignore_index=True)
            except:
                st.session_state.final_df = new_df
        else:
            # Agar pehle se data session me hai to usme jodo
            if not st.session_state.final_df.empty:
                 st.session_state.final_df = pd.concat([st.session_state.final_df, new_df], ignore_index=True)
            else:
                 st.session_state.final_df = new_df
                 
        st.success("✅ Processing Done! Filters use karein.")

# --- 3. DISPLAY & FILTERS LOGIC ---

if not st.session_state.final_df.empty:
    df_display = st.session_state.final_df.copy()

    # --- APPLY FILTERS (Jo sidebar me select kiye) ---
    # A. Month Filter
    # Pehle options update karo
    available_months = df_display['Month'].unique().tolist()
    # Note: Streamlit re-run hota hai, isliye options dynamic hone chahiye
    if not filter_month: # Agar user ne kuch select nahi kiya to sab dikhao
        pass 
    else:
        df_display = df_display[df_display['Month'].isin(filter_month)]

    # B. Vendor Filter
    if filter_vendor:
        df_display = df_display[df_display['Party_Name'].isin(filter_vendor)]

    # C. VR Filter
    if filter_vr:
        df_display = df_display[df_display['VR_No'].isin(filter_vr)]

    # D. Status Filter (Paid/Unpaid)
    if filter_status == "Paid (Done)":
        df_display = df_display[df_display['Paid'] == True]
    elif filter_status == "Unpaid (Pending)":
        df_display = df_display[df_display['Paid'] == False]

    # --- SHOW EDITABLE TABLE (Checkbox Included) ---
    st.subheader("📊 Live Billing Register")
    
    edited_df = st.data_editor(
        df_display,
        column_config={
            "Paid": st.column_config.CheckboxColumn(
                "Payment Done?",
                help="Tick karein agar payment ho gayi",
                default=False,
            ),
            "Amount": st.column_config.NumberColumn(
                "Amount (Rs)",
                format="₹ %d"
            ),
        },
        disabled=["Date", "VR_No", "File_Name"], # Ye columns edit nahi honge (Safety)
        hide_index=True,
        num_rows="dynamic"
    )

    # --- SUMMARY METRICS ---
    total_amt = edited_df['Amount'].sum()
    paid_amt = edited_df[edited_df['Paid'] == True]['Amount'].sum()
    pending_amt = total_amt - paid_amt
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Bill Amount", f"₹ {total_amt:,.0f}")
    col2.metric("✅ Paid Amount", f"₹ {paid_amt:,.0f}")
    col3.metric("⏳ Pending Amount", f"₹ {pending_amt:,.0f}")

    # --- DOWNLOAD ---
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        edited_df.to_excel(writer, index=False)
        
    st.download_button(
        label="📥 Download Final Excel Report",
        data=buffer.getvalue(),
        file_name=f"Billing_Register_{datetime.now().strftime('%d%m%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

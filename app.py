import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
from datetime import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Jigri Billing Dashboard", page_icon="💰", layout="wide")

st.title("💰 Smart Billing Dashboard")
st.markdown("### Upload Bills -> Auto-Detect (Vendor vs Salary) -> Excel")
st.divider()

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Purana Data")
    existing_file = st.file_uploader("Purani Excel file (Optional):", type=["xlsx"])

# --- MAIN LOGIC ---
uploaded_pdfs = st.file_uploader("📄 Bills Upload Karein (Vendor ya Salary)", 
                                 type=["pdf"], accept_multiple_files=True)

if uploaded_pdfs:
    if st.button(f"🚀 Process {len(uploaded_pdfs)} Bills"):
        
        all_data = []
        progress_bar = st.progress(0)
        
        for index, pdf_file in enumerate(uploaded_pdfs):
            try:
                # 1. PDF Read Karna
                with pdfplumber.open(pdf_file) as pdf:
                    full_text = ""
                    for page in pdf.pages:
                        full_text += page.extract_text() + "\n"
                
                # --- INTELLIGENT EXTRACTION ---
                
                # A. VR Number
                vr_match = re.search(r"(VR No\.|DV No\.:|VR No)\s*(\d+)", full_text)
                vr_no = vr_match.group(2) if vr_match else "Not Found"

                # B. Date
                date_match = re.search(r"Date:[-]?\s*(\d{2}-\d{2}-\d{4})", full_text)
                date = date_match.group(1) if date_match else "Not Found"

                # C. Amount
                amt_match = re.search(r"(Total of above Rs|DV Total:|Total Amount)\s*(\d+)", full_text)
                amount = float(amt_match.group(2)) if amt_match else 0.0

                # D. PARTY NAME LOGIC (IFSC Count Method)
                # Hum IFSC Code pattern dhoondenge (4 letters + 0 + 6 chars)
                # Example: SBIN0004088
                ifsc_matches = re.findall(r'[A-Z]{4}0[A-Z0-9]{6}', full_text)
                unique_ifsc = len(set(ifsc_matches)) # Duplicate hata kar gino

                party_name = "Not Found"
                payment_type = "Vendor" # Default

                if unique_ifsc > 1:
                    # Agar 1 se zyada alag IFSC hain -> Salary Bill
                    party_name = "Salary/Group Payment (Multiple Parties)"
                    payment_type = "Salary"
                else:
                    # Agar 0 ya 1 IFSC hai -> Vendor Bill
                    payment_type = "Vendor"
                    lines = full_text.split('\n')
                    for i, line in enumerate(lines):
                        # IFSC wali line dhoondo
                        if any(code in line for code in ifsc_matches) or "SBIN" in line:
                            # Vendor ka naam aksar agli line mein hota hai
                            if i + 1 < len(lines):
                                potential_name = lines[i+1].strip()
                                # Agar naam valid lag raha ho (Number nahi hai)
                                if not potential_name.isdigit() and len(potential_name) > 2:
                                    party_name = potential_name
                                    break
                    
                    # Fallback: Agar naam nahi mila par Remarks mein kuch hai
                    if party_name == "Not Found":
                         # Remarks check (Sample logic)
                         if "Remarks" in full_text:
                             pass 

                # Add to List
                all_data.append({
                    "Date": date,
                    "VR_No": vr_no,
                    "Party_Name": party_name,
                    "Amount": amount,
                    "File_Name": pdf_file.name,
                    "Type": payment_type,
                    "Status": "Pending"
                })
                
            except Exception as e:
                st.error(f"Error in {pdf_file.name}: {e}")
            
            progress_bar.progress((index + 1) / len(uploaded_pdfs))

        # --- RESULT ---
        if all_data:
            new_df = pd.DataFrame(all_data)
            
            # --- SHOW DATA ---
            st.success("✅ Extraction Complete!")
            st.subheader("📊 Final Data")
            edited_df = st.data_editor(new_df, num_rows="dynamic")

            # --- DOWNLOAD ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                edited_df.to_excel(writer, index=False)
                
            st.download_button(
                label="📥 Download Excel File",
                data=buffer.getvalue(),
                file_name=f"Billing_Sheet_{datetime.now().strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

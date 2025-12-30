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
                
                # A. VR Number (Dono format handle karega)
                # Dhoond raha hai: "VR No. 0058" ya "DV No.: 0058"
                vr_match = re.search(r"(VR No\.|DV No\.:|VR No)\s*(\d+)", full_text)
                vr_no = vr_match.group(2) if vr_match else "Not Found"

                # B. Date (Dono format: "Date:-" aur "Date:")
                date_match = re.search(r"Date:[-]?\s*(\d{2}-\d{2}-\d{4})", full_text)
                date = date_match.group(1) if date_match else "Not Found"

                # C. Amount
                amt_match = re.search(r"(Total of above Rs|DV Total:|Total Amount)\s*(\d+)", full_text)
                amount = float(amt_match.group(2)) if amt_match else 0.0

                # D. PARTY NAME LOGIC (Sabse Zaroori)
                # Hum ginenge ki "Bank" kitni baar aaya hai.
                # Salary bill mein bohot baar "State Bank" ya "Axis Bank" aata hai.
                
                bank_count = full_text.count("State Bank") + full_text.count("Axis Bank") + full_text.count("IFSC")
                
                party_name = "Not Found"
                
                if bank_count > 2:
                    # Agar 2 se zyada baar bank dikha, matlab ye Group/Salary bill hai
                    party_name = "Salary/Group Payment (Multiple Parties)"
                else:
                    # Agar kam baar dikha, matlab Vendor bill hai -> Naam dhoondo
                    lines = full_text.split('\n')
                    for i, line in enumerate(lines):
                        # Logic: Jahan IFSC code ya Bank likha ho, uske aas-paas naam hota hai
                        if ("SBIN" in line or "IFSC" in line) and len(line) > 5:
                            # Vendor bill mein naam aksar agli line mein hota hai
                            if i + 1 < len(lines):
                                potential_name = lines[i+1].strip()
                                # Agar agli line number hai (Account No), to uske agli line check karo
                                if potential_name.isdigit() or len(potential_name) < 3:
                                    if i + 2 < len(lines):
                                        party_name = lines[i+2].strip()
                                else:
                                    party_name = potential_name
                            break
                    
                    # Agar upar wala logic fail ho jaye, to "Remarks" check karo
                    if party_name == "Not Found" or party_name == "":
                        party_name = "Vendor Payment (Name Check Pending)"

                # Add to List
                all_data.append({
                    "Date": date,
                    "VR_No": vr_no,
                    "Party_Name": party_name,
                    "Amount": amount,
                    "File_Name": pdf_file.name,
                    "Type": "Salary" if bank_count > 2 else "Vendor",
                    "Status": "Pending"
                })
                
            except Exception as e:
                st.error(f"Error in {pdf_file.name}: {e}")
            
            progress_bar.progress((index + 1) / len(uploaded_pdfs))

        # --- RESULT ---
        if all_data:
            new_df = pd.DataFrame(all_data)
            
            if existing_file:
                try:
                    old_df = pd.read_excel(existing_file)
                    final_df = pd.concat([old_df, new_df], ignore_index=True)
                    st.success("✅ Merge Successful!")
                except:
                    final_df = new_df
                    st.warning("⚠️ Purani file corrupt thi, sirf naya data dikha raha hoon.")
            else:
                final_df = new_df
                st.success("✅ Data Extraction Complete!")

            # Editable Table
            st.subheader("📊 Final Data (Aap yahan changes kar sakte hain)")
            edited_df = st.data_editor(final_df, num_rows="dynamic")

            # Download
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                edited_df.to_excel(writer, index=False)
                
            st.download_button(
                label="📥 Download Excel File",
                data=buffer.getvalue(),
                file_name=f"Billing_Sheet_{datetime.now().strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

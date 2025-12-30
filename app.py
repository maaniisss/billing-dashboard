import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
from datetime import datetime

st.set_page_config(page_title="Jigri Debugger", page_icon="🛠️")
st.title("🛠️ Billing App (Debug Mode)")

uploaded_pdfs = st.file_uploader("PDF Upload Karein", type=["pdf"], accept_multiple_files=True)

if uploaded_pdfs:
    if st.button("🔍 Check PDF Text"):
        for pdf_file in uploaded_pdfs:
            with pdfplumber.open(pdf_file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
            
            st.subheader(f"📄 File: {pdf_file.name}")
            
            # --- X-RAY SECTION (Ye dikhayega ki computer kya dekh raha hai) ---
            st.error("👇 Computer ne ye padha (Isse copy karke Jigri ko bhejein):")
            st.text_area("Raw Text Content:", full_text, height=300)
            
            # --- CHECKING KEYWORDS ---
            st.write("--- Keyword Check ---")
            if "V.R. no." in full_text:
                st.success("✅ 'V.R. no.' mil gaya!")
            else:
                st.warning("❌ 'V.R. no.' nahi mila.")
                
            if "Passed for payment" in full_text:
                st.success("✅ 'Passed for payment' mil gaya!")
            else:
                st.warning("❌ 'Passed for payment' nahi mila.")

               
        

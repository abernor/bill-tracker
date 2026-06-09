import streamlit as st
import pandas as pd
import json
from datetime import datetime
import re
from pathlib import Path
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from PyPDF2 import PdfReader

st.set_page_config(page_title="Bill Tracker System", layout="wide", initial_sidebar_state="expanded")
st.write("VERSION: PDF2 FIX")

# ===== MASTER DATA (untuk demo, nanti replace dengan Google Sheets) =====
MASTER_ITEMS = {
    'PUCUK': {'supplier_names': ['PUCHOK GORENG NIPIS', 'DP'], 'unit': 'PCS'},
    'BALL': {'supplier_names': ['QL BEBOLA GORENG', 'QLBG'], 'unit': 'PCS'},
    'TAUHU GORENG': {'supplier_names': ['TAHU GORENG', 'CTT'], 'unit': 'PCS'},
    'TAUHU BULAT': {'supplier_names': ['TAHU BUNGA', 'CTTB'], 'unit': 'PCS'},
    'CRAB STICK ROLL': {'supplier_names': ['DEFIRST CRABSTICK ROLL', 'DCS'], 'unit': 'PACK'},
    'VEGIEROLL': {'supplier_names': ['PFT VEGETABLE ROLL', 'VR'], 'unit': 'PACK'},
    'EMPAT SEGI': {'supplier_names': ['TAHU EMPAT SEGI', 'CTTSE'], 'unit': 'PCS'},
    'WANTAN': {'supplier_names': ['WANTAN BUNGA', 'CTW'], 'unit': 'PCS'},
    'CILI': {'supplier_names': ['CILI', 'CILI'], 'unit': 'PCS'},
    'BENDI': {'supplier_names': ['BENDI', 'KB'], 'unit': 'PCS'},
    'TAUHU PUTIH': {'supplier_names': ['TAHU PUTIH', 'CTTP'], 'unit': 'PCS'},
    'CHEESE HOTDOG': {'supplier_names': ['CHEESE SAUSAGES', 'CH'], 'unit': 'PACK'},
    'FISH N SOY': {'supplier_names': ['QL FISH & SOY', 'QLFS'], 'unit': 'PACK'},
    'ROUND CAKE PUTIH': {'supplier_names': ['IKAN KEK BULAT PUTIH', 'A3'], 'unit': 'PCS'},
    'ROUNDCAKE GORENG': {'supplier_names': ['QL IKAN BULAT GORENG', 'STP'], 'unit': 'PACK'},
    'OTAK AYAM': {'supplier_names': ['AYAM ROLL', 'KSA'], 'unit': 'PACK'},
    'OTAK ROLL': {'supplier_names': ['OTAK ROLL', 'KSO'], 'unit': 'PACK'},
    'OTAK MERAH': {'supplier_names': ['OTAK ROLL', 'KSO'], 'unit': 'PACK'},
    'KUE TIAW': {'supplier_names': ['KUIH TIAU', 'WKT'], 'unit': 'PCS'},
    'BOLA PUTIH': {'supplier_names': ['IKAN BOLA PUTIH', 'A1'], 'unit': 'PCS'},
    'KETAM SEPIT': {'supplier_names': ['QL CRAB CLAW', 'QLCC'], 'unit': 'PACK'},
    '4X7': {'supplier_names': ['JUMBO FISH BEAN CURD ( 4x7 )', '4X7'], 'unit': 'PACK'},
    'FISHCAKE': {'supplier_names': ['QL FISH KEK', 'QL'], 'unit': 'PACK'},
    'LOBSTER BALL': {'supplier_names': ['FIGO LOBSTER BALL', 'LTB'], 'unit': 'PACK'},
    'DIMSUM KUNING': {'supplier_names': ['DIM SUM KUNING ( 15 PCS )', 'TS'], 'unit': 'PACK'},
    'SEAWEED ROLL': {'supplier_names': ['ML CRABSTICK SEAWEED ROLL', 'ML'], 'unit': 'PACK'},
}

# ===== FUNCTIONS =====
def extract_pdf_data(pdf_file):
    """Extract data dari PDF bill"""

    try:
        pdf_reader = PdfReader(pdf_file)

        text = ""

        for page in pdf_reader.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"


        bill_data = {
            "bill_no": "",
            "date": "",
            "items": []
        }


        lines = text.split("\n")


        # Bill number & date
        for line in lines:

            if "CS-" in line:
                match = re.search(
                    r"CS-\d+",
                    line
                )

                if match:
                    bill_data["bill_no"] = match.group()


            if "Date" in line:

                match = re.search(
                    r"\d{2}/\d{2}/\d{4}",
                    line
                )

                if match:
                    bill_data["date"] = match.group()



        # Item extraction
        for line in lines:

            qty_match = re.search(
                r"(\d+)\s+(PCS|PACK|PKT)",
                line
            )

            if qty_match:

                qty = int(
                    qty_match.group(1)
                )

                uom = qty_match.group(2)

                description = line[
                    :qty_match.start()
                ].strip()


                bill_data["items"].append(
                    {
                        "item_code": (
                            description.split()[0]
                            if description else ""
                        ),
                        "description": description,
                        "qty": qty,
                        "uom": uom
                    }
                )


        return bill_data


    except Exception as e:

        st.error(
            f"PDF Error: {e}"
        )

        return None

def match_supplier_to_order(supplier_name, supplier_code):
    """Match supplier item name/code ke order item name"""
    best_match = None
    best_score = 0
    
    for order_item, info in MASTER_ITEMS.items():
        # Check supplier names
        for supplier_variant in info['supplier_names']:
            score = fuzz.token_set_ratio(supplier_name.upper(), supplier_variant.upper())
            if score > best_score:
                best_score = score
                best_match = order_item
        
        # Check supplier codes
        if supplier_code.upper() in info['supplier_names']:
            return order_item
    
    if best_score >= 80:
        return best_match
    
    return None

def calculate_cumulative(order_id, order_list, bill_history):
    """Calculate cumulative qty untuk order"""
    order = order_list[order_list['Order ID'] == order_id].iloc[0]
    
    previous_bills = bill_history[bill_history['Order ID'] == order_id]
    cumulative = {}
    
    for qty_col in ['Qty1', 'Qty2', 'Qty3', 'Qty4', 'Qty5']:
        total_qty = order[qty_col] if order[qty_col] > 0 else 0
        billed_qty = previous_bills[qty_col].sum() if len(previous_bills) > 0 else 0
        
        cumulative[qty_col] = {
            'expected': total_qty,
            'billed': billed_qty,
            'pending': total_qty - billed_qty
        }
    
    return cumulative

# ===== UI =====
st.title("📊 Bill Verification & Tracking System")
st.subheader("Chiang Tar Enterprise - ROSMIE GLOBAL ENTERPRISE")

tabs = st.tabs(["📤 Upload Bill", "📋 Master Data", "📊 Dashboard", "📈 Reports"])

with tabs[0]:
    st.header("Upload & Process Bill")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1️⃣ Upload PDF Bill")
        uploaded_file = st.file_uploader("Choose PDF bill file", type=['pdf'])
        
        if uploaded_file:
            st.success(f"✓ File uploaded: {uploaded_file.name}")
            
            with st.spinner("Extracting data from PDF..."):
                bill_data = extract_pdf_data(uploaded_file)
            
            if bill_data:
                st.success(f"✓ Bill No: {bill_data['bill_no']}")
                st.success(f"✓ Date: {bill_data['date']}")
                st.success(f"✓ Items extracted: {len(bill_data['items'])}")
    
    with col2:
        st.subheader("2️⃣ Select Order Reference")
        order_id = st.text_input("Enter Order ID (e.g., PO-001):")
        qty_combo = st.multiselect(
            "Which Qty combination for this bill?",
            options=['Qty1', 'Qty2', 'Qty3', 'Qty4', 'Qty5'],
            default=['Qty1', 'Qty2']
        )
    
    if uploaded_file and order_id and qty_combo:
        st.divider()
        st.subheader("3️⃣ Review Extracted Data")
        
        if bill_data:
            df_items = pd.DataFrame(bill_data['items'])
            
            # Add matching results
            df_items['Order Item'] = df_items.apply(
                lambda row: match_supplier_to_order(row['description'], row['item_code']),
                axis=1
            )
            
            df_items['Match Status'] = df_items['Order Item'].apply(
                lambda x: '✓ MATCHED' if x else '❌ NO MATCH'
            )
            
            st.dataframe(df_items, use_container_width=True)
            
            if st.button("✅ Confirm & Save to Tracker", key="confirm_bill"):
                st.success("Bill saved to tracker! Tracking updated.")
                st.balloons()

with tabs[1]:
    st.header("Master Items Mapping")
    st.info("This is the mapping between your Order names and Supplier names")
    
    df_master = pd.DataFrame([
        {
            'Order Item': item,
            'Supplier Names': ', '.join(info['supplier_names']),
            'Unit': info['unit']
        }
        for item, info in MASTER_ITEMS.items()
    ])
    
    st.dataframe(df_master, use_container_width=True)
    
    st.divider()
    st.subheader("✏️ Add/Edit Item Mapping")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        new_order_item = st.text_input("Order Item Name")
    with col2:
        new_supplier_names = st.text_input("Supplier Names (comma separated)")
    with col3:
        new_unit = st.selectbox("Unit", ['PCS', 'PACK', 'PKT'])
    
    if st.button("Add Item Mapping"):
        st.success(f"✓ Added: {new_order_item}")

with tabs[2]:
    st.header("Dashboard Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Bills", "0")
    with col2:
        st.metric("Matched Items", "0%")
    with col3:
        st.metric("Discrepancies", "0")
    with col4:
        st.metric("Over-billing", "0")
    
    st.divider()
    st.subheader("Recent Bills")
    st.info("No bills processed yet. Upload a bill to get started.")

with tabs[3]:
    st.header("Reports & Analytics")
    
    st.subheader("1️⃣ Cumulative Tracking by Order")
    st.info("Select an order to see cumulative quantities billed vs expected")
    
    order_filter = st.selectbox("Select Order ID:", options=['PO-001', 'PO-002', 'PO-003'])
    
    if order_filter:
        st.write(f"Tracking for: **{order_filter}**")
        
        # Sample data
        tracking_data = {
            'Qty Combo': ['Qty1+2', 'Qty3', 'Qty4', 'Qty5'],
            'Expected': [100, 50, 0, 50],
            'Billed': [100, 0, 0, 0],
            'Pending': [0, 50, 0, 50],
            'Status': ['✓ COMPLETE', '⏳ PENDING', '⏳ PENDING', '⏳ PENDING']
        }
        
        st.dataframe(pd.DataFrame(tracking_data), use_container_width=True)
    
    st.divider()
    st.subheader("2️⃣ Export Report")
    
    if st.button("📥 Export to Excel"):
        st.success("Report exported successfully!")

st.divider()
st.caption("Bill Tracker System v1.0 | Powered by Streamlit")


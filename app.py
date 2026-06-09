# Bill Tracker v2.3 - Fixed Secret Manager
import streamlit as st
import pandas as pd
import json
from datetime import datetime
import re
from fuzzywuzzy import fuzz
from PyPDF2 import PdfReader
import gspread
from google.oauth2 import service_account
from google.cloud import secretmanager

st.set_page_config(page_title="Bill Tracker System", layout="wide", initial_sidebar_state="expanded")
st.write("VERSION: Google Secret Manager v2.3 (Fixed)")

# ===== CONFIG =====
SHEET_URL = "https://docs.google.com/spreadsheets/d/1SPd9zV8rB2sxOdFsfAfQeYhpu2PU3G9haJQ3UU1ce6s/edit"
PROJECT_ID = "gen-lang-client-0946610758"
SECRET_NAME = "bill-tracker-credentials"


def load_credentials_from_secret():
    """Load Google credential dari Secret Manager"""
    try:
        client = secretmanager.SecretManagerServiceClient()

        secret_path = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"

        response = client.access_secret_version(
            request={"name": secret_path}
        )

        secret_json = response.payload.data.decode("UTF-8")

        return json.loads(secret_json)

    except Exception as e:
        st.error(f"❌ Secret Manager Error: {e}")
        return None


@st.cache_resource
def load_google_sheet():
    """Load Google Sheet"""
    try:
        creds_dict = load_credentials_from_secret()

        if creds_dict is None:
            return None

        scope = [
            "https://www.googleapis.com/auth/spreadsheets"
        ]

        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=scope
        )

        client = gspread.authorize(creds)

        sheet = client.open_by_url(SHEET_URL)

        worksheet = sheet.get_worksheet(0)

        data = worksheet.get_all_records()

        st.success(f"✅ Loaded {len(data)} items from Google Sheet")

        return pd.DataFrame(data)

    except Exception as e:
        st.error(f"❌ Google Sheet Error: {e}")
        return None


# Load order data
df_orders = load_google_sheet()
def load_google_sheet():
    """Load order data dari Google Sheets"""
    try:
        creds_dict = load_credentials_from_secret()

        if creds_dict is None:
            st.error("❌ Could not load credentials")
            return None

        scope = [
            "https://www.googleapis.com/auth/spreadsheets"
        ]

        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=scope
        )

        client = gspread.authorize(creds)

        sheet = client.open_by_url(SHEET_URL)

        worksheet = sheet.get_worksheet(0)

        data = worksheet.get_all_records()

        st.success(
            f"✅ Loaded {len(data)} items from Google Sheets"
        )

        return pd.DataFrame(data)

    except Exception as e:
        import traceback

        st.error("❌ Error loading Google Sheet:")
        st.code(traceback.format_exc())

        return None
# Load order data
df_orders = load_google_sheet()

# ===== MASTER DATA =====
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
    'AYAM ROLL': {'supplier_names': ['AYAM ROLL', 'KSA'], 'unit': 'PACK'},
    'OTAK ROLL': {'supplier_names': ['OTAK ROLL', 'KSO'], 'unit': 'PACK'},
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

        # Extract bill number & date
        for line in lines:
            if "CS-" in line:
                match = re.search(r"CS-\d+", line)
                if match:
                    bill_data["bill_no"] = match.group()
            if "Date" in line:
                match = re.search(r"\d{2}/\d{2}/\d{4}", line)
                if match:
                    bill_data["date"] = match.group()

        # Extract items
        for line in lines:
            qty_match = re.search(r"(\d+)\s+(PCS|PACK|PKT)", line)
            if qty_match:
                qty = int(qty_match.group(1))
                uom = qty_match.group(2)
                description = line[:qty_match.start()].strip()
                bill_data["items"].append({
                    "item_code": description.split()[0] if description else "",
                    "description": description,
                    "qty": qty,
                    "uom": uom
                })

        return bill_data
    except Exception as e:
        st.error(f"PDF Error: {e}")
        return None

def match_supplier_to_order(supplier_name):
    """Match supplier item name ke order item name"""
    best_match = None
    best_score = 0

    for order_item, info in MASTER_ITEMS.items():
        for supplier_variant in info['supplier_names']:
            score = fuzz.token_set_ratio(supplier_name.upper(), supplier_variant.upper())
            if score > best_score:
                best_score = score
                best_match = order_item

    return best_match if best_score >= 80 else None

def get_order_quantities(item_name):
    """Get expected quantities dari Google Sheet"""
    if df_orders is None:
        return {}

    item_row = df_orders[df_orders['Item'].str.upper() == item_name.upper()]
    if len(item_row) == 0:
        return {}

    row = item_row.iloc[0]
    return {
        'Qty1': int(row.get('Qty1', 0)) if pd.notna(row.get('Qty1')) else 0,
        'Qty2': int(row.get('Qty2', 0)) if pd.notna(row.get('Qty2')) else 0,
        'Qty3': int(row.get('Qty3', 0)) if pd.notna(row.get('Qty3')) else 0,
        'Qty4': int(row.get('Qty4', 0)) if pd.notna(row.get('Qty4')) else 0,
        'Qty5': int(row.get('Qty5', 0)) if pd.notna(row.get('Qty5')) else 0,
    }

# ===== UI =====
st.title("📊 Bill Verification & Tracking System")
st.subheader("Chiang Tar Enterprise - ROSMIE GLOBAL ENTERPRISE")

tabs = st.tabs(["📤 Upload Bill", "📋 Orders", "📊 Dashboard", "📈 Reports"])

with tabs[0]:
    st.header("Upload & Process Bill")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1️⃣ Upload PDF Bill")
        uploaded_file = st.file_uploader("Choose PDF bill file", type=['pdf'])
        bill_data = None

        if uploaded_file:
            st.success(f"✓ File uploaded: {uploaded_file.name}")
            with st.spinner("Extracting data from PDF..."):
                bill_data = extract_pdf_data(uploaded_file)

            if bill_data:
                st.success(f"✓ Bill No: {bill_data['bill_no']}")
                st.success(f"✓ Date: {bill_data['date']}")
                st.success(f"✓ Items extracted: {len(bill_data['items'])}")

    with col2:
        st.subheader("2️⃣ Select Qty Combination")
        qty_combo = st.multiselect(
            "Which Qty combination for this bill?",
            options=['Qty1', 'Qty2', 'Qty3', 'Qty4', 'Qty5'],
            default=['Qty1', 'Qty2']
        )

    if uploaded_file and qty_combo and bill_data:
        st.divider()
        st.subheader("3️⃣ Review & Match Results")

        df_items = pd.DataFrame(bill_data['items'])
        df_items['Order Item'] = df_items['description'].apply(match_supplier_to_order)
        df_items['Match Status'] = df_items['Order Item'].apply(lambda x: '✓ MATCHED' if x else '❌ NO MATCH')

        expected_qty_list = []
        for order_item in df_items['Order Item']:
            if order_item:
                qty_dict = get_order_quantities(order_item)
                qty_sum = sum([qty_dict.get(q, 0) for q in qty_combo])
                expected_qty_list.append(qty_sum)
            else:
                expected_qty_list.append(0)

        df_items['Expected Qty'] = expected_qty_list
        df_items['Variance'] = df_items['qty'] - df_items['Expected Qty']

        st.dataframe(df_items[['description', 'qty', 'Order Item', 'Expected Qty', 'Variance', 'Match Status']], use_container_width=True)

        discrepancies = df_items[df_items['Variance'] != 0]
        if len(discrepancies) > 0:
            st.warning(f"⚠️ Found {len(discrepancies)} discrepancies!")
            st.dataframe(discrepancies, use_container_width=True)

        if st.button("✅ Confirm & Save to Tracker"):
            st.success("Bill saved! Tracking updated.")
            st.balloons()

with tabs[1]:
    st.header("Order List from Google Sheets")
    if df_orders is not None:
        st.dataframe(df_orders, use_container_width=True)
        st.info(f"Total items: {len(df_orders)}")
    else:
        st.error("Could not load orders.")

with tabs[2]:
    st.header("Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Bills", "0")
    col2.metric("Matched", "0%")
    col3.metric("Discrepancies", "0")
    col4.metric("Over-billing", "0")

with tabs[3]:
    st.header("Reports")
    st.info("Reports coming soon...")

st.divider()
st.caption("Bill Tracker v2.3 | Google Secret Manager | Streamlit")

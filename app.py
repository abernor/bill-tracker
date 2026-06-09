# Bill Tracker v2.4 - Clean Google Sheet + Secret Manager

import streamlit as st
import pandas as pd
import json
import re
from fuzzywuzzy import fuzz
from PyPDF2 import PdfReader
import gspread
from google.oauth2 import service_account
from google.cloud import secretmanager


# ================= CONFIG =================

st.set_page_config(
    page_title="Bill Tracker System",
    layout="wide"
)

st.write("VERSION: Bill Tracker v2.4 Stable")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1SPd9zV8rB2sxOdFsfAfQeYhpu2PU3G9haJQ3UU1ce6s/edit"

PROJECT_ID = "gen-lang-client-0946610758"
SECRET_NAME = "bill-tracker-credentials"


# ================= SECRET MANAGER =================

def load_credentials_from_secret():

    try:
        client = secretmanager.SecretManagerServiceClient()

        name = (
            f"projects/{PROJECT_ID}/"
            f"secrets/{SECRET_NAME}/versions/latest"
        )

        response = client.access_secret_version(
            request={"name": name}
        )

        secret = response.payload.data.decode("UTF-8")

        return json.loads(secret)

    except Exception as e:
        st.error(f"❌ Secret Manager Error: {e}")
        return None


# ================= GOOGLE SHEET =================

@st.cache_resource
def load_google_sheet():

    try:

        creds_json = load_credentials_from_secret()

        if creds_json is None:
            return None


        scope = [
            "https://www.googleapis.com/auth/spreadsheets"
        ]


        creds = service_account.Credentials.from_service_account_info(
            creds_json,
            scopes=scope
        )


        client = gspread.Client(auth=creds)

        sheet = client.open_by_url(SHEET_URL)

        worksheet = sheet.get_worksheet(0)

        records = worksheet.get_all_records()

        st.success(
            f"✅ Google Sheet Loaded : {len(records)} items"
        )

        return pd.DataFrame(records)


    except Exception as e:

        st.error(f"❌ Google Sheet Error: {e}")

        return None



# LOAD DATA
df_orders = load_google_sheet()



# ================= MASTER ITEM =================


MASTER_ITEMS = {

"PUCUK":["PUCHOK GORENG NIPIS","DP"],
"BALL":["QL BEBOLA GORENG","QLBG"],
"TAUHU GORENG":["TAHU GORENG"],
"TAUHU BULAT":["TAHU BUNGA"],
"CRAB STICK ROLL":["CRABSTICK"],
"VEGIEROLL":["VEGETABLE ROLL"],
"EMPAT SEGI":["TAHU EMPAT"],
"WANTAN":["WANTAN"],
"CILI":["CILI"],
"BENDI":["BENDI"],
"CHEESE HOTDOG":["CHEESE"],
"FISH N SOY":["FISH SOY"],
"AYAM ROLL":["AYAM ROLL"],
"OTAK ROLL":["OTAK ROLL"],
"FISHCAKE":["FISH KEK"],
"LOBSTER BALL":["LOBSTER"]

}



# ================= PDF =================


def extract_pdf_data(pdf_file):

    try:

        reader = PdfReader(pdf_file)

        text = ""

        for page in reader.pages:

            if page.extract_text():

                text += page.extract_text()


        items=[]


        for line in text.split("\n"):

            m = re.search(
                r"(\d+)\s+(PCS|PACK|PKT)",
                line
            )

            if m:

                items.append({

                    "description": line[:m.start()],
                    "qty": int(m.group(1))

                })


        return items


    except Exception as e:

        st.error(e)

        return []



# ================= MATCH =================


def match_item(name):

    best=None
    score=0


    for item,keys in MASTER_ITEMS.items():

        for k in keys:

            s=fuzz.token_set_ratio(
                name.upper(),
                k.upper()
            )

            if s > score:

                score=s
                best=item


    if score >= 70:

        return best

    return "NO MATCH"



# ================= UI =================


st.title("📊 Bill Verification & Tracking System")

st.subheader(
    "Chiang Tar Enterprise - ROSMIE GLOBAL ENTERPRISE"
)


tabs = st.tabs(
[
"📤 Upload Bill",
"📋 Orders",
"📊 Dashboard"
]
)



# Upload

with tabs[0]:

    st.header("Upload PDF Bill")


    file = st.file_uploader(
        "Choose PDF",
        type="pdf"
    )


    if file:

        data = extract_pdf_data(file)

        result=[]

        for x in data:

            result.append({

            "Supplier Item":x["description"],
            "Bill Qty":x["qty"],
            "Match":match_item(x["description"])

            })


        st.dataframe(
            pd.DataFrame(result),
            use_container_width=True
        )




# Orders

with tabs[1]:

    st.header("Google Sheet Orders")


    if df_orders is not None:

        st.dataframe(
            df_orders,
            use_container_width=True
        )

    else:

        st.warning(
            "No Google Sheet Data"
        )



# Dashboard

with tabs[2]:

    st.metric(
        "System",
        "ONLINE"
    )



st.caption(
"Bill Tracker v2.4 | Google Cloud Run | Streamlit"
)

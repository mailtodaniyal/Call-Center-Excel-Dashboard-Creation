import requests
import pandas as pd
import gspread
import streamlit as st
import plotly.express as px
import schedule
import time
from sqlalchemy import create_engine
from google.oauth2.service_account import Credentials

SERVICE_TITAN_API_KEY = "your_service_titan_api_key"
THREE_CX_API_KEY = "your_3cx_api_key"
GOOGLE_SHEETS_CREDENTIALS = "your_google_creds.json"
SHEET_ID = "your_google_sheet_id"
DATABASE_URL = "postgresql://user:password@localhost/call_center_db"

engine = create_engine(DATABASE_URL)

def fetch_service_titan_data():
    url = "https://api.servicetitan.io/calls"
    headers = {"Authorization": f"Bearer {SERVICE_TITAN_API_KEY}"}
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else []

def fetch_3cx_data():
    url = "https://api.3cx.com/calls"
    headers = {"Authorization": f"Bearer {THREE_CX_API_KEY}"}
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else []

def fetch_google_sheets_data(sheet_name):
    creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)
    return sheet.get_all_records()

def store_data_to_db(data, table_name):
    df = pd.DataFrame(data)
    df.to_sql(table_name, engine, if_exists="replace", index=False)

def process_call_data(call_data):
    df = pd.DataFrame(call_data)
    
    if df.empty:
        return 0, pd.DataFrame(), pd.Series()

    df['call_duration'] = df['call_duration'].astype(float)
    df['call_date'] = pd.to_datetime(df['call_date'])

    avg_call_duration = df['call_duration'].mean()
    agent_performance = df.groupby('agent_name')['call_duration'].mean().reset_index()
    customer_satisfaction = df.groupby('customer_feedback')['call_id'].count()

    return avg_call_duration, agent_performance, customer_satisfaction

def update_data():
    service_titan_data = fetch_service_titan_data()
    three_cx_data = fetch_3cx_data()
    google_forms_data = fetch_google_sheets_data("Form Responses")
    combined_data = service_titan_data + three_cx_data + google_forms_data
    store_data_to_db(combined_data, "call_data")

schedule.every(5).minutes.do(update_data)

st.set_page_config(page_title="Call Center Dashboard", layout="wide")

st.title("Call Center Dashboard")

service_titan_data = fetch_service_titan_data()
three_cx_data = fetch_3cx_data()
google_forms_data = fetch_google_sheets_data("Form Responses")

combined_data = service_titan_data + three_cx_data + google_forms_data
avg_call_duration, agent_performance, customer_satisfaction = process_call_data(combined_data)

st.metric("Average Call Duration", f"{avg_call_duration:.2f} mins")

st.subheader("Agent Performance")
if not agent_performance.empty:
    fig_agent = px.bar(agent_performance, x="agent_name", y="call_duration", title="Agent Performance")
    st.plotly_chart(fig_agent)
else:
    st.warning("No data available for agent performance.")

st.subheader("Customer Satisfaction")
if not customer_satisfaction.empty:
    fig_satisfaction = px.pie(names=customer_satisfaction.index, values=customer_satisfaction.values, title="Customer Feedback Distribution")
    st.plotly_chart(fig_satisfaction)
else:
    st.warning("No data available for customer satisfaction.")

while True:
    schedule.run_pending()
    time.sleep(60)

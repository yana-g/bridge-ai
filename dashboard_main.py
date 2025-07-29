import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# ========== Load environment variables ==========
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "bridge_db")

if not MONGO_URI:
    st.error("MONGO_URI not found in environment. Please check your .env file.")
    st.stop()

# ========== Connect to MongoDB ==========
try:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    records = list(db.qa_records.find().sort("timestamp", -1))
    user_records = list(db.users.find())
except Exception as e:
    st.error(f"Error connecting to MongoDB: {str(e)}")
    st.stop()

# ========== Build user type map ==========
user_df = pd.DataFrame(user_records)
user_df["username"] = user_df["username"].astype(str).str.strip().str.lower()
user_df["user_type"] = user_df["user_type"].fillna("unknown").astype(str).str.strip().str.lower()
user_df["User Type"] = user_df["user_type"]
user_type_map = dict(zip(user_df["username"], user_df["User Type"]))

# ========== Prepare QA Data ==========
data = []
for r in records:
    uid = r.get("user_id")
    user_id = uid.strip().lower() if isinstance(uid, str) else "guest"
    user_type = user_type_map.get(user_id, "guest")
    data.append({
        "Date": r.get("timestamp"),
        "User": user_id,
        "Question": r.get("question", ""),
        "Answer": r.get("answer", ""),
        "Model": r.get("metadata", {}).get("model", "unknown"),
        "Confidence": r.get("metadata", {}).get("confidence"),
        "Tokens": r.get("metadata", {}).get("tokens"),
        "COT Steps": r.get("metadata", {}).get("cot_steps"),
        "User Type": user_type,
    })

df = pd.DataFrame(data)

if df.empty:
    st.warning("No records found in qa_records collection.")
    st.stop()

# ========== Process ==========
df["Date_dt"] = pd.to_datetime(df["Date"])
df["COT Summary"] = df["COT Steps"].apply(lambda steps: " → ".join(steps) if isinstance(steps, list) else "")

# ========== Streamlit UI ==========
st.set_page_config(page_title="BRIDGE Dashboard", layout="wide", page_icon="📊")
st.markdown("""
    <h1 style='display: flex; align-items: center;'>
        <span style='font-size: 2.5rem;'>📊 BRIDGE Dashboard</span>
    </h1>
    <p style='font-size: 2rem; color: grey;'>Real-time insights from MongoDB logs</p>
""", unsafe_allow_html=True)

# Filters
with st.container():
    c1, c2, c3, _ = st.columns([1, 1, 1, 6])
    with c1:
        start_date = st.date_input("Start Date", datetime.today() - timedelta(days=30))
    with c2:
        end_date = st.date_input("End Date", datetime.today())
    with c3:
        selected_model = st.selectbox("LLM Model", ["All"] + sorted(df["Model"].dropna().unique()))

filtered_df = df[(df["Date_dt"].dt.date >= start_date) & (df["Date_dt"].dt.date <= end_date)]
if selected_model != "All":
    filtered_df = filtered_df[filtered_df["Model"] == selected_model]

# KPI Metrics
k1, k2, k3, k4 = st.columns(4)
k1.metric("🔢 Total Queries", len(filtered_df))
k2.metric("🧠 Avg Tokens", f"{filtered_df['Tokens'].dropna().mean():.1f}" if filtered_df['Tokens'].notna().any() else "N/A")
k3.metric("👤 Unique Query Senders", filtered_df['User'].nunique())
k4.metric("📂 Registered Users", len(user_df.drop_duplicates(subset="username")))

# Row 1: Model Usage / User Types
row1_col1, row1_col2 = st.columns([2, 1])
row2_col1, row2_col2 = st.columns([2, 1])

with row1_col2:
    st.subheader("👥 User Types")
    pie_combined = pd.concat([
        user_df[["User Type"]],
        df[df["User Type"] == "guest"]["User Type"].to_frame()  # Include guests from questions
    ], ignore_index=True)

    user_type_counts = pie_combined["User Type"].value_counts().reset_index()
    user_type_counts.columns = ["User Type", "Count"]
    user_type_counts["Count"] = pd.to_numeric(user_type_counts["Count"], errors="coerce").fillna(0).astype(int)
    user_type_counts["Percent"] = (user_type_counts["Count"] / user_type_counts["Count"].sum() * 100).round(1).astype(str) + "%"

    fig2 = px.pie(
        user_type_counts,
        names="User Type",
        values="Count",
        color_discrete_sequence=px.colors.qualitative.Set3,
        hole=0.3
    )
    fig2.update_traces(textinfo='percent+label')
    st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(user_type_counts, use_container_width=True)


with row1_col1:
    st.subheader("🎯 Avg Answer Confidence")
    if filtered_df["Confidence"].notna().any():
        avg_conf = filtered_df["Confidence"].mean()
        st.metric("Average Confidence", f"{avg_conf:.1%}")
    else:
        st.info("No confidence data available.")

    st.subheader("📝 Recent Queries")
    st.dataframe(filtered_df[["Date", "User", "Question", "Model"]].head(10), use_container_width=True)

# Top Users
st.subheader("👑 Top Users by Activity")
top_users = (
    filtered_df.groupby("User")
    .agg(
        Num_Queries=("Question", "count"),
        Avg_Confidence=("Confidence", "mean"),
        User_Type=("User Type", "first")
    )
    .reset_index()
    .sort_values(by="Num_Queries", ascending=False)
)
top_n = 5 if len(top_users) > 5 else len(top_users)
st.dataframe(top_users.head(top_n), use_container_width=True)

# Drilldown
st.subheader("🔍 Drilldown by User")
unique_users = filtered_df["User"].unique().tolist()
selected_user = st.selectbox("Select a user to explore", unique_users)
user_df_selected = filtered_df[filtered_df["User"] == selected_user]
if not user_df_selected.empty:
    st.markdown(f"**Total Queries:** {len(user_df_selected)}")
    st.dataframe(user_df_selected[["Date", "Question", "Model", "Confidence", "Tokens", "COT Summary"]], use_container_width=True)
else:
    st.info("No data available for selected user.")


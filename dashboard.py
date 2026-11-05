
import boto3, os, json
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

@st.cache_data(ttl=30)
def load_logs_from_s3():
    bucket_name = os.getenv("S3_BUCKET")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-2")

    if not bucket_name:
        raise ValueError("S3_BUCKET is not configured.")

    s3 = boto3.client("s3", region_name=region)

    logs = []

    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(
        Bucket=bucket_name,
        Prefix="raw-logs/"
    ):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if not key.endswith(".jsonl"):
                continue

            response = s3.get_object(
                Bucket=bucket_name,
                Key=key
            )

            content = response["Body"].read().decode("utf-8")

            for line in content.splitlines():
                if not line.strip():
                    continue

                try:
                    log = json.loads(line)
                    log["source_file"] = key
                    logs.append(log)

                except json.JSONDecodeError:
                    continue

    return pd.DataFrame(logs)

st.set_page_config(
    page_title="Cloud Log Analyzer",
    layout="wide"
)

try:
    df = load_logs_from_s3()
except Exception as e:
    st.error(f"Failed to load logs from S3: {e}")
    st.stop()

if df.empty:
    st.warning("No logs found in S3.")
    st.stop()

st.sidebar.title("LOG ANALYZER")
st.sidebar.caption("Cloud-based Log Analyzer & Monitoring")

if st.button("Refresh Logs"):
    st.cache_data.clear()
    st.rerun()

page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Log Explorer", "Validation", "Threats"]
)

st.title("Security Monitoring Dashboard")
st.caption("Monitor authentication logs and suspicious activities")

if page == "Overview":

    total_logs = len(df)
    successful = (df["status"] == "success").sum()
    failed = (df["status"] == "failure").sum()

    st.subheader("System Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Logs", total_logs)
    col2.metric("Successful Logins", successful)
    col3.metric("Failed Logins", failed)
    col4.metric("Invalid Logs", 0)

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Login Status")
        status_counts = df["status"].value_counts()
        st.bar_chart(status_counts)

    with right:
        st.subheader("Recent Activity")
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

elif page == "Log Explorer":

    st.subheader("Log Explorer")

    selected_status = st.selectbox(
        "Filter by status",
        ["All", "success", "failure"]
    )

    filtered_df = df.copy()

    if selected_status != "All":
        filtered_df = filtered_df[
            filtered_df["status"] == selected_status
        ]

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True
    )

elif page == "Validation":

    st.subheader("Log Validation")
    st.info("Validation details will be connected to the collector.")

elif page == "Threats":

    st.subheader("Suspicious Activities")
    st.info("Threat detection results will be connected here.")

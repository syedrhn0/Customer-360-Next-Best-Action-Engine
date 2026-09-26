import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Customer 360 & NBA Engine", layout="wide")

session = get_active_session()

st.title("Customer 360 & Next Best Action Engine")
st.caption("AI-powered customer intelligence using Snowflake Cortex")

st.divider()


@st.cache_data(ttl=300)
def load_customer_list():
    df = session.sql(
        "SELECT customer_id, customer_name FROM CUSTOMER_360_DB.PUBLIC.CUSTOMER_NBA ORDER BY customer_id"
    ).to_pandas()
    return df


try:
    customer_list = load_customer_list()
except Exception as e:
    st.error(f"Failed to load customer list: {e}")
    st.stop()

customer_options = {
    f"{row['CUSTOMER_NAME']} (ID: {row['CUSTOMER_ID']})": row["CUSTOMER_ID"]
    for _, row in customer_list.iterrows()
}

selected_label = st.selectbox("Select a customer", options=list(customer_options.keys()))
selected_id = customer_options[selected_label]

try:
    row = session.sql(
        f"SELECT * FROM CUSTOMER_360_DB.PUBLIC.CUSTOMER_NBA WHERE customer_id = {selected_id}"
    ).to_pandas()
except Exception as e:
    st.error(f"Failed to load customer data: {e}")
    st.stop()

if row.empty:
    st.warning("No data found for the selected customer.")
    st.stop()

c = row.iloc[0]

st.divider()

# --- Customer Profile ---
st.subheader("Customer Profile")
col1, col2, col3 = st.columns(3)
col1.metric("Customer Name", c["CUSTOMER_NAME"])
col2.metric("Customer ID", int(c["CUSTOMER_ID"]))
col3.metric("Age", int(c["AGE"]))

col4, col5, col6 = st.columns(3)
col4.metric("City", c["CITY"])
col5.metric("Segment", c["CUSTOMER_SEGMENT"])
col6.metric("Customer Since", str(c["CUSTOMER_SINCE"]))

st.divider()

# --- Customer Activity ---
st.subheader("Customer Activity")
col1, col2, col3 = st.columns(3)
col1.metric("Total Spend (INR)", f"₹{int(c['TOTAL_SPEND']):,}")
col2.metric("Purchase Count", int(c["PURCHASE_COUNT"]))
col3.metric("Last Purchase Date", str(c["LAST_PURCHASE_DATE"]) if c["LAST_PURCHASE_DATE"] else "N/A")

col4, col5, col6 = st.columns(3)
days_purchase = int(c["DAYS_SINCE_PURCHASE"]) if c["DAYS_SINCE_PURCHASE"] is not None else "N/A"
col4.metric("Days Since Purchase", days_purchase)
col5.metric("Interaction Count", int(c["INTERACTION_COUNT"]))
col6.metric(
    "Last Interaction Date",
    str(c["LAST_INTERACTION_DATE"]) if c["LAST_INTERACTION_DATE"] else "N/A",
)

col7, col8, col9 = st.columns(3)
sentiment = round(float(c["AVG_SENTIMENT_SCORE"]), 2) if c["AVG_SENTIMENT_SCORE"] is not None else "N/A"
col7.metric("Avg Sentiment Score", sentiment)
col8.metric("Complaint Count", int(c["COMPLAINT_COUNT"]))
col9.metric("Open Complaints", int(c["OPEN_COMPLAINTS"]))

st.divider()

# --- Next Best Action ---
st.subheader("Next Best Action")

risk = c["RISK_LEVEL"]
risk_colors = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
risk_icon = risk_colors.get(risk, "⚪")

col1, col2 = st.columns(2)
col1.metric("Risk Level", f"{risk_icon} {risk}")
col2.metric("Next Best Action", c["NEXT_BEST_ACTION"])
st.info(f"**Action Reason:** {c['ACTION_REASON']}")

st.divider()

# --- AI Explanation ---
st.subheader("AI Explanation")

if st.button("Generate AI Explanation"):
    with st.spinner("Generating AI explanation using Snowflake Cortex..."):
        try:
            context_row = session.sql(
                f"SELECT ai_context FROM CUSTOMER_360_DB.PUBLIC.CUSTOMER_AI_CONTEXT WHERE customer_id = {selected_id}"
            ).to_pandas()

            if context_row.empty:
                st.error("No AI context found for this customer.")
            else:
                ai_context = context_row.iloc[0]["AI_CONTEXT"]
                prompt = (
                    "You are a customer relationship analyst. "
                    "Based ONLY on the data below, provide a concise explanation (under 120 words) covering:\n"
                    "1. Why this customer received the assigned next best action.\n"
                    "2. What customer signals support the recommendation.\n"
                    "3. What a customer-service or sales employee should do next.\n\n"
                    "Clearly distinguish observed data from the recommendation. "
                    "Do not invent facts beyond what is provided.\n\n"
                    f"Customer Data:\n{ai_context}"
                )
                escaped = prompt.replace("'", "''")
                result = session.sql(
                    f"SELECT AI_COMPLETE('llama3.1-70b', '{escaped}') AS explanation"
                ).to_pandas()
                st.markdown(result.iloc[0]["EXPLANATION"])
        except Exception as e:
            st.error(f"AI explanation failed: {e}")

st.divider()
st.caption("Powered by Snowflake Cortex")

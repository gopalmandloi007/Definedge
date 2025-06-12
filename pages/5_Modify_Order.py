import streamlit as st
from integrate import ConnectToIntegrate, IntegrateOrders

# --- LOGIN BLOCK ---
api_token = st.secrets["integrate_api_token"]
api_secret = st.secrets["integrate_api_secret"]
uid = st.secrets["integrate_uid"]
actid = st.secrets["integrate_actid"]
api_session_key = st.secrets["integrate_api_session_key"]
ws_session_key = st.secrets["integrate_ws_session_key"]

conn = ConnectToIntegrate()
conn.login(api_token, api_secret)
conn.set_session_keys(uid, actid, api_session_key, ws_session_key)
io = IntegrateOrders(conn)

st.title("Modify Existing Order")

with st.form("modify_order_form"):
    order_id = st.text_input("Order ID", value="25060300007644")
    price = st.number_input("New Price", value=1905.0)
    quantity = st.number_input("New Quantity", value=2, step=1)
    price_type = st.selectbox("Price Type", options=["LIMIT", "MARKET"], index=0)
    exchange = st.selectbox("Exchange", options=["NSE", "BSE"], index=0)
    order_type = st.selectbox("Order Type", options=["BUY", "SELL"], index=0)
    product_type = st.selectbox("Product Type", options=["CNC", "MIS"], index=0)
    tradingsymbol = st.text_input("Symbol", value="BDL-EQ")
    submitted = st.form_submit_button("Modify Order")
    if submitted:
        modify_kwargs = dict(
            order_id=order_id,
            price=price,
            quantity=quantity,
            price_type=conn.PRICE_TYPE_LIMIT if price_type == "LIMIT" else conn.PRICE_TYPE_MARKET,
            exchange=conn.EXCHANGE_TYPE_NSE if exchange == "NSE" else conn.EXCHANGE_TYPE_BSE,
            order_type=conn.ORDER_TYPE_BUY if order_type == "BUY" else conn.ORDER_TYPE_SELL,
            product_type=conn.PRODUCT_TYPE_CNC if product_type == "CNC" else conn.PRODUCT_TYPE_MIS,
            tradingsymbol=tradingsymbol,
        )
        try:
            order = io.modify_order(**modify_kwargs)
            st.success(f"Order modified successfully! Details: {order}")
        except Exception as e:
            st.error(f"Order modification failed: {e}")

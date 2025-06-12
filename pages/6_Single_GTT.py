import streamlit as st
from integrate import ConnectToIntegrate, IntegrateOrders

st.title("Place Single GTT Order")

def get_credentials():
    secrets = st.secrets
    return (
        secrets["integrate_api_token"],
        secrets["integrate_api_secret"],
        secrets["integrate_uid"],
        secrets["integrate_actid"],
        secrets["integrate_api_session_key"],
        secrets["integrate_ws_session_key"],
    )

def get_io():
    api_token, api_secret, uid, actid, api_session_key, ws_session_key = get_credentials()
    conn = ConnectToIntegrate()
    conn.login(api_token, api_secret)
    conn.set_session_keys(uid, actid, api_session_key, ws_session_key)
    return conn, IntegrateOrders(conn)

conn, io = get_io()
with st.form("single_gtt_form"):
    tradingsymbol = st.text_input("Symbol", value="BDL-EQ")
    exchange = st.selectbox("Exchange", options=["NSE", "BSE"], index=0)
    order_type = st.selectbox("Order Type", options=["BUY", "SELL"], index=1)
    quantity = st.number_input("Quantity", value=1, step=1)
    trigger_price = st.number_input("Trigger Price", value=1850.0)
    price = st.number_input("Order Price", value=1855.0)
    remarks = st.text_input("Remarks", value="Single GTT via API")
    submitted = st.form_submit_button("Place GTT")
    if submitted:
        order_kwargs = dict(
            tradingsymbol=tradingsymbol,
            exchange=conn.EXCHANGE_TYPE_NSE if exchange == "NSE" else conn.EXCHANGE_TYPE_BSE,
            order_type=conn.ORDER_TYPE_SELL if order_type == "SELL" else conn.ORDER_TYPE_BUY,
            quantity=str(quantity),
            alert_price=str(trigger_price),
            price=str(price),
            condition="LTP_BELOW"
        )
        try:
            response = io.place_gtt_order(**order_kwargs)
            st.success(f"Single GTT order placed! {response}")
        except Exception as e:
            st.error(f"Single GTT placement failed: {e}")

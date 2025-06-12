import streamlit as st
from integrate import ConnectToIntegrate, IntegrateOrders

st.title("Place OCO GTT Order")

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
with st.form("oco_gtt_form"):
    tradingsymbol = st.text_input("Symbol", value="MRPL-EQ")
    exchange = st.selectbox("Exchange", options=["NSE", "BSE"], index=0)
    order_type = st.selectbox("Order Type", options=["BUY", "SELL"], index=1)
    target_quantity = st.number_input("Target Quantity", value=93, step=1)
    stoploss_quantity = st.number_input("Stoploss Quantity", value=371, step=1)
    target_price = st.number_input("Target Price", value=164.0)
    stoploss_price = st.number_input("Stoploss Price", value=144.0)
    remarks = st.text_input("Remarks", value="OCO GTT via API")
    submitted = st.form_submit_button("Place OCO GTT")
    if submitted:
        order_kwargs = dict(
            tradingsymbol=tradingsymbol,
            exchange=conn.EXCHANGE_TYPE_NSE if exchange == "NSE" else conn.EXCHANGE_TYPE_BSE,
            order_type=conn.ORDER_TYPE_SELL if order_type == "SELL" else conn.ORDER_TYPE_BUY,
            target_quantity=str(target_quantity),
            stoploss_quantity=str(stoploss_quantity),
            target_price=str(target_price),
            stoploss_price=str(stoploss_price),
            remarks=remarks
        )
        try:
            response = io.place_oco_order(**order_kwargs)
            st.success(f"OCO GTT order placed! {response}")
        except Exception as e:
            st.error(f"OCO GTT placement failed: {e}")

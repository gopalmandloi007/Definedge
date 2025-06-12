import streamlit as st
import math
import requests
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

st.title("CNC Buy Order")

ORDER_PARAMS = dict(
    tradingsymbol="HPL-EQ",
    quantity=0,
    amount=55000,
    price=588,
    price_type="L",
    exchange="N",
    product_type="CNC",
    order_type="B",
    validity="DAY"
)

def fetch_ltp(exchange, tradingsymbol):
    symbol_token_map = {
        "TEXRAIL-EQ": "5489",
        "SBIN-EQ": "3045",
    }
    token = symbol_token_map.get(tradingsymbol)
    if not token:
        return None
    exg = "NSE" if str(exchange).upper().startswith("N") else "BSE"
    url = f"https://integrate.definedgesecurities.com/dart/v1/quotes/{exg}/{token}"
    headers = {'Authorization': api_session_key}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return float(data.get('ltp')) if data.get('ltp') not in (None, "null", "") else None
    except Exception:
        pass
    return None

params = ORDER_PARAMS.copy()
with st.form("order_form"):
    tradingsymbol = st.text_input("Symbol", value=params["tradingsymbol"])
    qty = st.number_input("Quantity", value=params["quantity"], min_value=0, step=1)
    amt = st.number_input("Amount (Rs)", value=params["amount"], min_value=0)
    price = st.number_input("Price", value=params["price"], min_value=0.0)
    price_type = st.selectbox("Price Type", options=["L", "M"], index=0)
    order_type = st.selectbox("Order Side", options=["B", "S"], index=0)
    submitted = st.form_submit_button("Place Order")
    if submitted:
        params.update(
            tradingsymbol=tradingsymbol,
            quantity=qty,
            amount=amt,
            price=price,
            price_type=price_type,
            order_type=order_type
        )
        # Resolve shortcuts
        params['exchange'] = "NSE" if str(params['exchange']).upper() in ("N", "NSE") else "BSE"
        params['order_type'] = "BUY" if params["order_type"] == "B" else "SELL"
        params['price_type'] = "LIMIT" if params["price_type"] == "L" else "MARKET"
        use_amount = params["amount"] > 0
        final_qty = params["quantity"]
        use_price = params["price"]
        if use_amount:
            if params["price_type"] == "LIMIT" and use_price > 0:
                pass
            else:
                ltp = fetch_ltp(params["exchange"], params["tradingsymbol"])
                use_price = ltp if ltp else use_price
            if use_price:
                final_qty = math.floor(params["amount"] / use_price)
        if final_qty < 1:
            st.error("Order quantity must be at least 1.")
        else:
            order_kwargs = dict(
                exchange=conn.EXCHANGE_TYPE_NSE if params["exchange"] == "NSE" else conn.EXCHANGE_TYPE_BSE,
                order_type=conn.ORDER_TYPE_BUY if params["order_type"] == "BUY" else conn.ORDER_TYPE_SELL,
                price=use_price,
                price_type=conn.PRICE_TYPE_LIMIT if params["price_type"] == "LIMIT" else conn.PRICE_TYPE_MARKET,
                product_type=conn.PRODUCT_TYPE_CNC,
                quantity=int(final_qty),
                tradingsymbol=params["tradingsymbol"],
            )
            try:
                order = io.place_order(**order_kwargs)
                st.success(f"Order placed successfully! Details: {order}")
            except Exception as e:
                st.error(f"Order placement failed: {e}")

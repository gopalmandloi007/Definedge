import streamlit as st
import math
import requests
from integrate import ConnectToIntegrate, IntegrateOrders

# --- Session/Secrets ---
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

BASE_URL = "https://integrate.definedgesecurities.com/dart/v1"
HEADERS = {"Authorization": api_session_key}

st.set_page_config(page_title="Order Dashboard", layout="wide")
st.title("Order Management: Broker Style (Minimal Fields)")

# --- Minimal Modify Form ---
def minimal_modify_form(order, on_submit=None):
    order_id = order.get('order_id') or order.get('alert_id') or ""
    st.markdown(f"**{order.get('tradingsymbol', '')}** | {order_id}")
    with st.form(f"mod_form_{order_id}", clear_on_submit=True):
        side = st.selectbox(
            "Side", ["BUY", "SELL"], 
            index=0 if order.get("order_type", "SELL")=="BUY" else 1
        )
        qty = st.number_input(
            "Quantity", 
            min_value=1, 
            value=int(order.get('quantity') or order.get('target_quantity') or order.get('stoploss_quantity') or 1)
        )
        price_type_val = order.get("price_type", "LIMIT")
        price_type = st.selectbox(
            "Order Type", ["LIMIT", "MARKET"],
            index=0 if price_type_val.startswith("L") else 1
        )
        price_val = order.get('price') or order.get('target_price') or order.get('stoploss_price') or 0.0
        price = st.number_input("Price", min_value=0.0, value=float(price_val))
        submitted = st.form_submit_button("Submit Modify")
        if submitted and on_submit:
            return on_submit(
                side=side,
                qty=qty,
                price_type=price_type,
                price=price,
                order=order
            )

# --- Layout ---
col1, col2, col3 = st.columns([1.7, 1.7, 1.6])

# --- 1. LIVE ORDER BOOK: Modify/Cancel ---
with col1:
    st.subheader("Order Book")
    try:
        r = requests.get(f"{BASE_URL}/orders", headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        orders = data.get("orders", [])
        if not orders:
            st.info("No orders found.")
        else:
            df = []
            for o in orders:
                df.append({
                    "ID": o.get("order_id", ""),
                    "Symbol": o.get("tradingsymbol", ""),
                    "Side": o.get("order_type", ""),
                    "Qty": o.get("quantity", ""),
                    "Type": o.get("price_type", ""),
                    "Status": o.get("order_status", ""),
                    "Price": o.get("price", ""),
                    "Time": o.get("order_entry_time", "")
                })
            st.dataframe(df, height=300, use_container_width=True)
            idx = st.selectbox("Select Order for Action", options=list(range(1, len(orders)+1)), format_func=lambda x: f"{orders[x-1]['tradingsymbol']} ({orders[x-1]['order_id']})" if orders else "")
            selected = orders[idx-1]
            st.caption(f"Order: {selected['tradingsymbol']} | {selected['order_id']} ({selected['order_status']})")
            c1, c2 = st.columns(2)
            with c1:
                with st.expander("Modify", expanded=False):
                    def handle_modify(side, qty, price_type, price, order):
                        kwargs = {
                            "order_id": order.get("order_id"),
                            "tradingsymbol": order["tradingsymbol"],
                            "order_type": side,
                            "quantity": int(qty),
                            "price_type": price_type,
                            "price": float(price),
                            "exchange": order.get("exchange"),
                            "product_type": order.get("product_type"),
                        }
                        try:
                            resp = io.modify_order(**kwargs)
                            st.success(f"Order Modified: {resp}")
                        except Exception as e:
                            st.error(f"Failed: {e}")
                    minimal_modify_form(selected, on_submit=handle_modify)
            with c2:
                if st.button("Cancel Order"):
                    try:
                        resp = io.cancel_order(order_id=selected.get("order_id"))
                        st.success(f"Order Cancelled: {resp}")
                    except Exception as e:
                        st.error(f"Cancel failed: {e}")

# --- 2. NEW CNC BUY/SELL ORDER ---
with col2:
    st.subheader("Place CNC Buy/Sell")
    with st.form("cnc_form", clear_on_submit=True):
        tradingsymbol = st.text_input("Symbol (e.g. SBIN-EQ)", value="HPL-EQ")
        side = st.selectbox("Order Side", ["BUY", "SELL"])
        quantity = st.number_input("Quantity (set 0 if using amount)", min_value=0, value=0, step=1)
        amount = st.number_input("Total Amount (Rs)", min_value=0, value=55000)
        price = st.number_input("Limit Price (for Market, leave as 0)", min_value=0.0, value=588.0)
        price_type = st.selectbox("Price Type", ["LIMIT", "MARKET"])
        exchange = st.selectbox("Exchange", ["NSE", "BSE"])
        validity = st.selectbox("Validity", ["DAY", "IOC"])
        submitted = st.form_submit_button("Place Order")
        if submitted:
            try:
                use_amount = amount > 0
                use_price = price if price_type == "LIMIT" and price > 0 else None
                ltp = None
                if use_amount and (use_price is None or use_price == 0):
                    token_map = {"TEXRAIL-EQ": "5489", "SBIN-EQ": "3045"}
                    token = token_map.get(tradingsymbol)
                    if token:
                        url = f"{BASE_URL}/quotes/{exchange}/{token}"
                        res = requests.get(url, headers=HEADERS, timeout=10)
                        if res.status_code == 200:
                            ltp = float(res.json().get('ltp'))
                    if ltp:
                        use_price = ltp
                final_qty = int(quantity)
                if use_amount and use_price:
                    final_qty = math.floor(amount / use_price)
                if final_qty < 1:
                    st.error("Order quantity must be at least 1 after calculation.")
                else:
                    order_kwargs = dict(
                        tradingsymbol=tradingsymbol,
                        exchange=conn.EXCHANGE_TYPE_NSE if exchange == "NSE" else conn.EXCHANGE_TYPE_BSE,
                        order_type=conn.ORDER_TYPE_BUY if side == "BUY" else conn.ORDER_TYPE_SELL,
                        price=price,
                        price_type=conn.PRICE_TYPE_LIMIT if price_type == "LIMIT" else conn.PRICE_TYPE_MARKET,
                        product_type=conn.PRODUCT_TYPE_CNC,
                        quantity=final_qty
                    )
                    resp = io.place_order(**order_kwargs)
                    st.success(f"Order Placed! Response: {resp}")
            except Exception as e:
                st.error(f"Order Placement Failed: {e}")

# --- 3. GTT Order Book/Action ---
with col3:
    st.subheader("GTT Order Book")
    try:
        r = requests.get(f"{BASE_URL}/gttorders", headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        orders = data.get("pendingGTTOrderBook") or next((v for v in data.values() if isinstance(v, list)), [])
        if not orders:
            st.info("No GTT orders found.")
        else:
            df = []
            for o in orders:
                df.append({
                    "ID": o.get("alert_id", ""),
                    "Symbol": o.get("tradingsymbol", ""),
                    "Type": "OCO" if o.get("stoploss_price") else "Single",
                    "Qty": o.get("quantity", o.get("target_quantity", "")),
                    "Trig": o.get("trigger_price", o.get("target_trigger", "")),
                    "Price": o.get("price", o.get("target_price", "")),
                    "Status": o.get("status", ""),
                    "Time": o.get("order_time", "")
                })
            st.dataframe(df, height=300, use_container_width=True)
            idx = st.selectbox("Select GTT for Action", options=list(range(1, len(orders)+1)), format_func=lambda x: f"{orders[x-1]['tradingsymbol']} ({orders[x-1]['alert_id']})" if orders else "")
            selected = orders[idx-1]
            st.caption(f"GTT: {selected['tradingsymbol']} | {selected['alert_id']} ({selected.get('status', '')})")
            c1, c2 = st.columns(2)
            with c1:
                with st.expander("Modify GTT", expanded=False):
                    def handle_gtt_modify(side, qty, price_type, price, order):
                        payload = {
                            "alert_id": order.get("alert_id"),
                            "tradingsymbol": order.get("tradingsymbol"),
                            "order_type": side,
                            "quantity": int(qty),
                            "price_type": price_type,
                            "price": float(price),
                            "exchange": order.get("exchange"),
                            "product_type": order.get("product_type", "CNC"),
                        }
                        try:
                            url = f"{BASE_URL}/gttmodify"
                            resp = requests.post(url, headers={**HEADERS, "Content-Type": "application/json"}, json=payload)
                            st.success(f"GTT Modified: {resp.json()}")
                        except Exception as e:
                            st.error(f"Failed: {e}")
                    minimal_modify_form(selected, on_submit=handle_gtt_modify)
            with c2:
                if st.button("Cancel GTT"):
                    alert_id = selected.get("alert_id")
                    is_oco = bool(selected.get("stoploss_price"))
                    if is_oco:
                        url = f"{BASE_URL}/ococancel/{alert_id}"
                    else:
                        url = f"{BASE_URL}/gttcancel/{alert_id}"
                    resp = requests.get(url, headers=HEADERS)
                    st.success(f"GTT Cancelled: {resp.json()}")
    except Exception as e:
        st.error(f"Failed to fetch GTT order book: {e}")

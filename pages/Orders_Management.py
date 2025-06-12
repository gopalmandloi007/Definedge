import streamlit as st
import math
from integrate import ConnectToIntegrate, IntegrateOrders
import requests

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

st.set_page_config(page_title="Order/GTT Dashboard", layout="wide")
st.title("Order & GTT Full Dashboard")

tabs = st.tabs([
    "Place CNC Order",
    "Modify/Cancel Orders",
    "Place GTT (Single/OCO)",
    "GTT Book/Modify/Cancel"
])

# --- 1. Place CNC BUY/SELL ORDER ---
with tabs[0]:
    st.subheader("Place New CNC Buy/Sell Order")
    with st.form("cnc_order_form", clear_on_submit=True):
        tradingsymbol = st.text_input("Symbol (e.g. SBIN-EQ)", value="HPL-EQ")
        side = st.selectbox("Order Side", ["BUY", "SELL"])
        quantity = st.number_input("Quantity (set 0 if using amount)", min_value=0, value=0, step=1)
        amount = st.number_input("Total Amount (Rs)", min_value=0, value=55000)
        price = st.number_input("Limit Price (for Market, leave as 0)", min_value=0.0, value=588.0)
        price_type = st.selectbox("Price Type", ["LIMIT", "MARKET"])
        exchange = st.selectbox("Exchange", ["NSE", "BSE"])
        validity = st.selectbox("Validity", ["DAY", "IOC"])
        product_type = "CNC"

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

# --- 2. MODIFY/CANCEL EXISTING ORDERS (Order Book) ---
with tabs[1]:
    st.subheader("Live Order Book (Modify/Cancel)")
    try:
        # Fetch order book via REST if available, else via io
        r = requests.get(f"{BASE_URL}/orders", headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        orders = data.get("orders", [])
        if not orders:
            st.info("No orders found.")
        else:
            df = []
            for o in orders:
                df.append({k: o.get(k, "") for k in [
                    "order_id", "tradingsymbol", "exchange", "order_type", "price_type", "product_type",
                    "quantity", "pending_qty", "filled_qty", "price", "order_status", "order_entry_time"
                ]})
            st.dataframe(df, use_container_width=True)
            for i, o in enumerate(orders):
                exp = st.expander(f"{o.get('tradingsymbol')} | {o.get('order_id')} | {o.get('order_status')}")
                with exp:
                    st.json(o)
                    col1, col2 = st.columns(2)
                    if st.session_state.get(f"modify_{i}", False):
                        with st.form(f"form_mod_{i}", clear_on_submit=True):
                            new_price = st.number_input("New Price", value=float(o.get("price", 0)), key=f"price_{i}")
                            new_qty = st.number_input("New Qty", value=int(o.get("quantity", 0)), key=f"qty_{i}")
                            submitted = st.form_submit_button("Modify")
                            if submitted:
                                try:
                                    kwargs = dict(
                                        order_id=o.get("order_id"),
                                        price=new_price,
                                        quantity=new_qty,
                                        price_type=o.get("price_type"),
                                        exchange=o.get("exchange"),
                                        order_type=o.get("order_type"),
                                        product_type=o.get("product_type"),
                                        tradingsymbol=o.get("tradingsymbol"),
                                    )
                                    resp = io.modify_order(**kwargs)
                                    st.success(f"Order Modified: {resp}")
                                except Exception as e:
                                    st.error(f"Failed: {e}")
                                st.session_state[f"modify_{i}"] = False
                        if st.button("Close", key=f"close_mod_{i}"):
                            st.session_state[f"modify_{i}"] = False
                    else:
                        if col1.button("Modify", key=f"modifybtn_{i}"):
                            st.session_state[f"modify_{i}"] = True
                        if col2.button("Cancel", key=f"cancelbtn_{i}"):
                            try:
                                resp = io.cancel_order(order_id=o.get("order_id"))
                                st.success(f"Order Cancelled: {resp}")
                            except Exception as e:
                                st.error(f"Cancel failed: {e}")

    except Exception as e:
        st.error(f"Failed to fetch order book: {e}")

# --- 3. PLACE SINGLE/OCO GTT ---
with tabs[2]:
    st.subheader("Place GTT (Single/OCO)")
    t = st.radio("Type", ["Single", "OCO"])
    with st.form("gtt_form", clear_on_submit=True):
        tradingsymbol = st.text_input("Symbol", value="MRPL-EQ")
        exchange = st.selectbox("Exchange", ["NSE", "BSE"])
        order_type = st.selectbox("Order Type", ["BUY", "SELL"])
        quantity = st.number_input("Quantity", value=1, step=1)
        remarks = st.text_input("Remarks", value="GTT via API")
        if t == "Single":
            trigger_price = st.number_input("Trigger Price", value=1850.0)
            price = st.number_input("Order Price", value=1855.0)
        else:
            target_quantity = st.number_input("Target Quantity", value=93, step=1)
            stoploss_quantity = st.number_input("Stoploss Quantity", value=371, step=1)
            target_price = st.number_input("Target Price", value=164.0)
            stoploss_price = st.number_input("Stoploss Price", value=144.0)
        submitted = st.form_submit_button("Place GTT")
        if submitted:
            try:
                if t == "Single":
                    kwargs = dict(
                        tradingsymbol=tradingsymbol,
                        exchange=conn.EXCHANGE_TYPE_NSE if exchange == "NSE" else conn.EXCHANGE_TYPE_BSE,
                        order_type=conn.ORDER_TYPE_SELL if order_type == "SELL" else conn.ORDER_TYPE_BUY,
                        quantity=str(quantity),
                        alert_price=str(trigger_price),
                        price=str(price),
                        condition="LTP_BELOW"
                    )
                    resp = io.place_gtt_order(**kwargs)
                else:
                    kwargs = dict(
                        tradingsymbol=tradingsymbol,
                        exchange=conn.EXCHANGE_TYPE_NSE if exchange == "NSE" else conn.EXCHANGE_TYPE_BSE,
                        order_type=conn.ORDER_TYPE_SELL if order_type == "SELL" else conn.ORDER_TYPE_BUY,
                        target_quantity=str(target_quantity),
                        stoploss_quantity=str(stoploss_quantity),
                        target_price=str(target_price),
                        stoploss_price=str(stoploss_price),
                        remarks=remarks
                    )
                    resp = io.place_oco_order(**kwargs)
                st.success(f"GTT Placed: {resp}")
            except Exception as e:
                st.error(f"GTT failed: {e}")

# --- 4. GTT Book/Modify/Cancel ---
with tabs[3]:
    st.subheader("GTT Book: View/Modify/Cancel")
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
                df.append({k: o.get(k, "") for k in [
                    "alert_id", "tradingsymbol", "exchange", "order_type", "product_type", "quantity", "price", "trigger_price",
                    "target_price", "target_quantity", "stoploss_price", "stoploss_quantity", "remarks", "order_time"
                ]})
            st.dataframe(df, use_container_width=True)
            for i, o in enumerate(orders):
                exp = st.expander(f"GTT: {o.get('tradingsymbol')} | {o.get('alert_id')}")
                with exp:
                    st.json(o)
                    col1, col2 = st.columns(2)
                    if col1.button("Modify", key=f"gttmod_{i}"):
                        is_oco = any([o.get(f) for f in ("stoploss_price", "stoploss_trigger", "target_price", "target_trigger")])
                        if is_oco:
                            new_target_trigger = st.text_input("Target Trigger", value=str(o.get('target_trigger', '')), key=f"tgttrig_{i}")
                            new_target_price = st.text_input("Target Price", value=str(o.get('target_price', '')), key=f"tgtpr_{i}")
                            new_stoploss_trigger = st.text_input("Stoploss Trigger", value=str(o.get('stoploss_trigger', '')), key=f"sltrig_{i}")
                            new_stoploss_price = st.text_input("Stoploss Price", value=str(o.get('stoploss_price', '')), key=f"slpr_{i}")
                            new_target_qty = st.text_input("Target Qty", value=str(o.get('target_quantity', '')), key=f"tgtqty_{i}")
                            new_stoploss_qty = st.text_input("Stoploss Qty", value=str(o.get('stoploss_quantity', '')), key=f"slqty_{i}")
                            if st.button("Modify OCO", key=f"gttmodbtn_{i}"):
                                data = {
                                    "tradingsymbol": o.get("tradingsymbol"),
                                    "exchange": o.get("exchange"),
                                    "order_type": o.get("order_type"),
                                    "target_quantity": new_target_qty,
                                    "stoploss_quantity": new_stoploss_qty,
                                    "target_price": new_target_price,
                                    "stoploss_price": new_stoploss_price,
                                    "alert_id": o.get("alert_id"),
                                    "remarks": "modified by Streamlit",
                                    "product_type": o.get("product_type", "CNC"),
                                }
                                url = f"{BASE_URL}/ocomodify"
                                resp = requests.post(url, headers={**HEADERS, "Content-Type": "application/json"}, json=data)
                                st.write(resp.json())
                        else:
                            new_trigger = st.text_input("Trigger Price", value=str(o.get('trigger_price', '')), key=f"gtttrig_{i}")
                            new_price = st.text_input("Order Price", value=str(o.get('price', '')), key=f"gttpr_{i}")
                            new_qty = st.text_input("Quantity", value=str(o.get('quantity', '')), key=f"gttqty_{i}")
                            if st.button("Modify GTT", key=f"gttmodbtn_s_{i}"):
                                data = {
                                    "exchange": o.get("exchange"),
                                    "alert_id": o.get("alert_id"),
                                    "tradingsymbol": o.get("tradingsymbol"),
                                    "condition": o.get("condition"),
                                    "order_type": o.get("order_type"),
                                    "alert_price": new_trigger,
                                    "price": new_price,
                                    "quantity": new_qty
                                }
                                url = f"{BASE_URL}/gttmodify"
                                resp = requests.post(url, headers={**HEADERS, "Content-Type": "application/json"}, json=data)
                                st.write(resp.json())
                    if col2.button("Cancel", key=f"gttcxl_{i}"):
                        alert_id = o.get("alert_id")
                        is_oco = any([o.get(f) for f in ("stoploss_price", "stoploss_trigger", "target_price", "target_trigger")])
                        if is_oco:
                            url = f"{BASE_URL}/ococancel/{alert_id}"
                        else:
                            url = f"{BASE_URL}/gttcancel/{alert_id}"
                        resp = requests.get(url, headers=HEADERS)
                        st.write(resp.json())
    except Exception as e:
        st.error(f"Failed to fetch GTT order book: {e}")

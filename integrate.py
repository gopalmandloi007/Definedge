import requests

class ConnectToIntegrate:
    BASE_URL = "https://integrate.definedgesecurities.com/dart/v1"

    # Useful constants for order types, exchanges, etc.
    EXCHANGE_TYPE_NSE = "NSE"
    EXCHANGE_TYPE_BSE = "BSE"
    ORDER_TYPE_BUY = "BUY"
    ORDER_TYPE_SELL = "SELL"
    PRICE_TYPE_LIMIT = "LIMIT"
    PRICE_TYPE_MARKET = "MARKET"
    PRODUCT_TYPE_CNC = "CNC"
    PRODUCT_TYPE_MIS = "MIS"

    def __init__(self):
        self.api_token = None
        self.api_secret = None
        self.uid = None
        self.actid = None
        self.api_session_key = None
        self.ws_session_key = None

    def login(self, api_token, api_secret):
        self.api_token = api_token
        self.api_secret = api_secret

    def set_session_keys(self, uid, actid, api_session_key, ws_session_key):
        self.uid = uid
        self.actid = actid
        self.api_session_key = api_session_key
        self.ws_session_key = ws_session_key

    def get_session_keys(self):
        return (self.uid, self.actid, self.api_session_key, self.ws_session_key)

    @property
    def headers(self):
        base = {
            "x-api-key": self.api_token,
            "x-api-secret": self.api_secret,
        }
        if self.api_session_key:
            base["Authorization"] = self.api_session_key
        return base

class IntegrateOrders:
    def __init__(self, conn):
        self.conn = conn

    def holdings(self):
        url = f"{self.conn.BASE_URL}/holdings"
        resp = requests.get(url, headers=self.conn.headers)
        resp.raise_for_status()
        return resp.json()

    def positions(self):
        url = f"{self.conn.BASE_URL}/positions"
        resp = requests.get(url, headers=self.conn.headers)
        resp.raise_for_status()
        return resp.json()

    def orders(self):
        url = f"{self.conn.BASE_URL}/orders"
        resp = requests.get(url, headers=self.conn.headers)
        resp.raise_for_status()
        return resp.json()

    def gtt_orders(self):
        url = f"{self.conn.BASE_URL}/gttorders"
        resp = requests.get(url, headers=self.conn.headers)
        resp.raise_for_status()
        return resp.json()

    def trade_book(self):
        """
        Return the trade book. Uses '/trades' endpoint (not '/tradebook')!
        """
        url = f"{self.conn.BASE_URL}/trades"
        resp = requests.get(url, headers=self.conn.headers)
        resp.raise_for_status()
        return resp.json()

    def place_order(self, tradingsymbol, exchange, order_type, price, price_type, product_type, quantity):
        url = f"{self.conn.BASE_URL}/placeorder"
        data = {
            "tradingsymbol": tradingsymbol,
            "exchange": exchange,
            "order_type": order_type,
            "price": price,
            "price_type": price_type,
            "product_type": product_type,
            "quantity": quantity,
        }
        resp = requests.post(url, headers=self.conn.headers, json=data)
        resp.raise_for_status()
        return resp.json()

    def modify_order(self, order_id, tradingsymbol, exchange, order_type, price, price_type, product_type, quantity):
        url = f"{self.conn.BASE_URL}/modify"
        data = {
            "order_id": order_id,
            "tradingsymbol": tradingsymbol,
            "exchange": exchange,
            "order_type": order_type,
            "price": price,
            "price_type": price_type,
            "product_type": product_type,
            "quantity": quantity,
        }
        resp = requests.post(url, headers=self.conn.headers, json=data)
        resp.raise_for_status()
        return resp.json()

    def place_gtt_order(self, tradingsymbol, exchange, order_type, quantity, alert_price, price, condition):
        url = f"{self.conn.BASE_URL}/gttplace"
        data = {
            "tradingsymbol": tradingsymbol,
            "exchange": exchange,
            "order_type": order_type,
            "quantity": quantity,
            "alert_price": alert_price,
            "price": price,
            "condition": condition,
        }
        resp = requests.post(url, headers=self.conn.headers, json=data)
        resp.raise_for_status()
        return resp.json()

    def place_oco_order(self, tradingsymbol, exchange, order_type, target_quantity, stoploss_quantity, target_price, stoploss_price, remarks):
        url = f"{self.conn.BASE_URL}/ocoplace"
        data = {
            "tradingsymbol": tradingsymbol,
            "exchange": exchange,
            "order_type": order_type,
            "target_quantity": target_quantity,
            "stoploss_quantity": stoploss_quantity,
            "target_price": target_price,
            "stoploss_price": stoploss_price,
            "remarks": remarks,
        }
        resp = requests.post(url, headers=self.conn.headers, json=data)
        resp.raise_for_status()
        return resp.json()

    # --- Optional: Add GTT Modify/Cancel/OCO Modify/Cancel methods if required ---
    def modify_gtt_order(self, data):
        url = f"{self.conn.BASE_URL}/gttmodify"
        resp = requests.post(url, headers={**self.conn.headers, "Content-Type": "application/json"}, json=data)
        resp.raise_for_status()
        return resp.json()

    def modify_oco_order(self, data):
        url = f"{self.conn.BASE_URL}/ocomodify"
        resp = requests.post(url, headers={**self.conn.headers, "Content-Type": "application/json"}, json=data)
        resp.raise_for_status()
        return resp.json()

    def cancel_gtt_order(self, alert_id):
        url = f"{self.conn.BASE_URL}/gttcancel/{alert_id}"
        resp = requests.get(url, headers=self.conn.headers)
        resp.raise_for_status()
        return resp.json()

    def cancel_oco_order(self, alert_id):
        url = f"{self.conn.BASE_URL}/ococancel/{alert_id}"
        resp = requests.get(url, headers=self.conn.headers)
        resp.raise_for_status()
        return resp.json()

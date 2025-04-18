from prunpy.data_loader import loader
from prunpy.constants import BOGUS_ORDER_THRESHOLD
import json

class Exchange:
    def __init__(self, rawdata, exchange_goods):
        if isinstance(rawdata, str):
            rawexchanges = fio.request("GET", "/exchange/station", cache='forever')
            for rawexchange in rawexchanges:
                if rawexchange['ComexCode'] == rawdata:
                    rawdata = rawexchange

        self.rawdata = rawdata
        self.ticker = rawdata.get('ComexCode')
        self.code = self.ticker
        self.name = rawdata.get('ComexName')
        self.currency = rawdata.get('CurrencyCode')
        self.country = rawdata.get('CountryCode')
        self.system_natural_id = rawdata.get('SystemNaturalId')

        goods = {}

        self.goods = exchange_goods

    def get_good(self, material_ticker):
        return self.goods.get(material_ticker, None)

    def get_average_price(self, material_ticker, buy_or_sell, amount):
        good = self.goods[material_ticker]
        if buy_or_sell == "Buy":
            pass

    #def get_availability(self, material_ticker, buy_or_sell):
    #    good = self.goods[material_ticker]

    def get_price_history(self, material_ticker):
        return loader.get_price_history(self.ticker, material_ticker)

    def get_raw_local_market_data(self):
        market_name = self.name.replace(" Commodity Exchange", "")
        if not market_name.endswith(" Station"):
            market_name += " Station"
        market_name = market_name.replace(" ", "%20")
        
        try:
            request_url = f"/localmarket/planet/{market_name}"
            print(f"Requesting {request_url}")
            rawdata = prun.fio.request("GET", request_url)
            return rawdata
        except:
            print(f"Failed to get market data for {market_name}")
            return {
                "ShippingAds": [],
                "BuyingAds": [],
                "SellingAds": [],
            }



    def __str__(self):
        return f"[Exchange {self.ticker}]"

class ExchangeGood:
    def __init__(self, rawdata):
        self.rawdata = rawdata
        self.ticker = rawdata['MaterialTicker']
        self.name = rawdata['MaterialName']
        self.currency = rawdata['Currency']
        #self.recently_traded = rawdata['Traded']
        self.exchange_code = rawdata['ExchangeCode']

        self._init_buy_orders() # AKA Bid
        self._init_sell_orders() # AKA Ask


    def _init_buy_orders(self):
        raw_orders = self.rawdata['BuyingOrders'] # AKA Bid
        # Remap ItemCount to count and ItemCost to cost
        self.buy_orders = []
        for raw_order in raw_orders:
            order = {}
            order['cost'] = raw_order['ItemCost']
            order['count'] = raw_order['ItemCount']
            order['company_name'] = raw_order['CompanyName']
            self.buy_orders.append(order)
        self.buy_orders = sorted(self.buy_orders, key=lambda k: k['cost'], reverse=True)

        # Fixes values for nation orders with no count limit
        for order in self.buy_orders:
            if not order['count']:
                order['count'] = float('inf')

        # Filter bogus orders
        if len(self.buy_orders) > 0:
            filtered_orders = []
            buy_min = self.buy_orders[0]['cost'] / BOGUS_ORDER_THRESHOLD
            for i in range(len(self.buy_orders)):
                order = self.buy_orders[i]
                if order['cost'] >= buy_min:
                    filtered_orders.append(order)
            self.buy_orders = filtered_orders

    def _init_sell_orders(self):
        raw_orders = self.rawdata['SellingOrders']  # AKA Ask
        # Remap ItemCount to count and ItemCost to cost
        self.sell_orders = []
        for raw_order in raw_orders:
            order = {}
            order['cost'] = raw_order['ItemCost']
            order['count'] = raw_order['ItemCount']
            order['company_name'] = raw_order['CompanyName']
            self.sell_orders.append(order)
        self.sell_orders = sorted(self.sell_orders, key=lambda k: k['cost'])

        # Fixes values for nation orders with no count limit
        for order in self.sell_orders:
            if not order['count']:
                order['count'] = float('inf')

        # Filter bogus orders
        if len(self.sell_orders) > 0:
            filtered_orders = []
            sell_max = self.sell_orders[0]['cost'] * BOGUS_ORDER_THRESHOLD
            for i in range(len(self.sell_orders)):
                order  = self.sell_orders[i]
                if order['cost'] <= sell_max:
                    filtered_orders.append(order)
            self.sell_orders  = filtered_orders


    @property
    def buy_price(self):
        if len(self.sell_orders) > 0:
            return self.sell_orders[0]['cost']
        else:
            return float('inf')

    @property
    def sell_price(self):
        if len(self.buy_orders) > 0:
            return self.buy_orders[0]['cost']
        else:
            return 0

    def buy_price_for_amount(self, amount):
        met = 0
        spent = 0
        for order in self.sell_orders:
            needed = amount - met
            if order['count'] >= needed:
                bought = needed
                spent += bought * order['cost']
                met = amount
                break
            else:
                bought = order['count']
                met += bought
                spent += bought * order['cost']

        if met < amount:
            return float('inf')
        else:
            return spent

    def sell_price_for_amount(self, amount):
        met = 0
        earned = 0
        for order in self.buy_orders:
            needed = amount - met
            if order['count'] >= needed:
                sold = needed
                earned += sold * order['cost']
                met = amount
                break
            else:
                sold = order['count']
                met += sold
                earned += sold * order['cost']

        if met < amount:
            return 0
        else:
            return earned

    def estimate_price_movement(self, short_window=3, long_window=14):
        """
        Estimate the price movement based on the difference between short-term
        and long-term moving averages.

        :param short_window: The window size for the short-term moving average.
        :param long_window: The window size for the long-term moving average.
        :return: A percentage value indicating the price movement, or 0 if values are invalid.
        """
        price_history_interval = self.price_history.intervals['DAY_ONE']  # Using DAY_ONE interval

        # Get the most recent moving averages
        short_ma = price_history_interval.get_moving_average(0, short_window)
        long_ma = price_history_interval.get_moving_average(0, long_window)

        # Handle invalid or edge cases
        if (
            short_ma is None or long_ma is None or
            short_ma == float('inf') or long_ma == float('inf') or
            short_ma == 0 or long_ma == 0
        ):  return 0  # Movement is zero for invalid data or rare/inconsistent sales

        # Calculate the price movement as a percentage of the long-term moving average
        movement = (short_ma - long_ma) / long_ma * 100
        return movement



    @property
    def supply(self):
        if len(self.sell_orders) == 0:
            return 0

        total_count = 0
        for order in self.sell_orders:
            total_count += order['count']


        return total_count

    @property
    def demand(self):
        if len(self.buy_orders) == 0:
            return 0

        total_count = 0
        for order in self.buy_orders:
            total_count += order['count']

        return total_count

    @property
    def price_history(self):
        exchange = loader.get_exchange(self.exchange_code)
        return exchange.get_price_history(self.ticker)

    @property
    def daily_sold(self):
        return self.price_history.average_traded_daily
    @property
    def daily_traded(self):
        return self.daily_sold

    @property
    def spread_absolute(self):
        return self.buy_price - self.sell_price
    @property
    def spread_amount(self):
        return self.buy_price - self.sell_price

    @property
    def spread_ratio(self):
        return self.buy_price / self.sell_price
    @property
    def spread_percent(self):
        return (self.spread_ratio-1)*100

    @property
    def mm_buys(self):
        if len(self.buy_orders) > 0:
            return self.buy_orders[0]['count'] == float('inf')
        return False

    @property
    def mm_sells(self):
        if len(self.sell_orders) > 0:
            return self.sell_orders[0]['count'] == float('inf')
        return False

    def __str__(self):
        return f"[{self.ticker} at {self.exchange_code}]"
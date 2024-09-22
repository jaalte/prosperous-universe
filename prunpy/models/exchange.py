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

    def get_availability(self, material_ticker, buy_or_sell):
        good = self.goods[material_ticker]


    def __str__(self):
        return f"[Exchange {self.ticker}]"

class ExchangeGood:
    def __init__(self, rawdata):
        self.rawdata = rawdata
        self.ticker = rawdata['MaterialTicker']
        self.name = rawdata['MaterialName']
        self.currency = rawdata['Currency']
        self.recently_traded = rawdata['Traded']

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

    @property
    def supply(self):
        # Get average price for all orders
        #total_cost = sum([i['cost'] * i['count'] for i in self.sell_orders])
        if len(self.sell_orders) == 0:
            return 0

        total_count = 0
        for order in self.sell_orders:
            total_count += order['count']


        return total_count#, total_cost/total_count

    @property
    def demand(self):
        # Get average price for all orders
        #total_cost = sum([i['cost'] * i['count'] for i in self.buy_orders])
        if len(self.buy_orders) == 0:
            return 0

        total_count = 0
        for order in self.buy_orders:
            total_count += order['count']

        return total_count#, total_cost/total_count

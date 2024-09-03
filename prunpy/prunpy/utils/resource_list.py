import math

class ResourceList:
    def __init__(self, rawdata={}):
        if len(rawdata) == 0:
            self.resources = {}
            return

        if isinstance(rawdata, dict):
            self.resources = rawdata
        elif isinstance(rawdata, list):

            key_mapping = {
                'CommodityTicker': 'Ticker',
                'MaterialTicker': 'Ticker',
                'Ticker': 'Ticker',
                'MaterialAmount': 'Amount',
                'DailyConsumption': 'Amount',
                'Amount': 'Amount',
            }

            # Initialize ticker_key and amount_key with None
            ticker_key = None
            amount_key = None

            # Find the correct keys
            for key in key_mapping:
                if key in rawdata[0]:
                    if key_mapping[key] == 'Ticker' and ticker_key is None:
                        ticker_key = key
                    elif key_mapping[key] == 'Amount' and amount_key is None:
                        amount_key = key

            # Default to 'Ticker' and 'Amount' if no specific key found
            ticker_key = ticker_key or 'Ticker'
            amount_key = amount_key or 'Amount'

            self.resources = {}
            for resource in rawdata:
                ticker = resource[ticker_key]
                amount = resource[amount_key]
                self.resources[ticker] = amount
        elif isinstance(rawdata, str):
            from prunpy.data_loader import loader
            tickers = sorted(loader.materials_by_ticker.keys())

            pattern = r'\b(\d+)\s*x?\s*({})\b'.format('|'.join(re.escape(ticker) for ticker in tickers))
            matches = re.findall(pattern, rawdata)
            recognized_tickers = {ticker for _, ticker in matches}

            # Check for unrecognized tickers
            unrecognized = re.findall(r'(\d+\s*x?\s*[A-Z0-9]+)', rawdata)
            for item in unrecognized:
                quantity, ticker = re.findall(r'(\d+)\s*x?\s*([A-Z0-9]+)', item)[0]
                if ticker not in recognized_tickers:
                    print(f"Unrecognized material ticker: {ticker}")

            self.resources = {ticker: int(quantity) for quantity, ticker in matches}
        else:
            raise TypeError("Unsupported data type for ResourceList initialization")

        self.resources = dict(sorted(self.resources.items()))

    def get_material_properties(self):
        from prunpy.data_loader import loader
        return {ticker: loader.materials_by_ticker[ticker] for ticker in self.resources}

    def get_total_weight(self):
        from prunpy.data_loader import loader
        total = 0
        for ticker, amount in self.resources.items():
            total += loader.materials_by_ticker[ticker]['Weight'] * amount
        return total

    def get_total_volume(self):
        from prunpy.data_loader import loader
        total = 0
        for ticker, amount in self.resources.items():
            total += loader.materials_by_ticker[ticker]['Volume'] * amount
        return total

    def get_total_value(self, exchange="NC1", trade_type="buy"):
        from prunpy.game_importer import importer 
        if isinstance(exchange, str):
            exchange = importer.exchanges[exchange]

        if not isinstance(trade_type, str):
            return NotImplemented
        trade_type = trade_type.lower()

        total = 0
        for ticker, amount in self.resources.items():
            if trade_type == "buy":
                total += exchange.get_good(ticker).buy_price * amount
            else: # trade_type == "sell" or other:
                total += exchange.get_good(ticker).sell_price * amount
        return total

    def get_amount(self, ticker):
        return self.resources.get(ticker, 0)

    def contains(self, ticker):
        return ticker in self.resources.keys() and self.resources[ticker] > 0

    def remove(self, ticker):
        if ticker in self.resources:
            amount = self.resources[ticker]
            del self.resources[ticker]
            return amount
        else:
            raise KeyError(f"Resource '{ticker}' does not exist in the ResourceList.")

    def invert(self):
        new_resources = {ticker: -amount for ticker, amount in self.resources.items()}
        return ResourceList(new_resources)

    def prune_negatives(self):
        new_resources = {ticker: amount for ticker, amount in self.resources.items() if amount > 0}
        return ResourceList(new_resources)

    def floor(self):
        new_resources = {ticker: math.floor(amount) for ticker, amount in self.resources.items()}
        return ResourceList(new_resources)

    def ceil(self):
        new_resources = {ticker: math.ceil(amount) for ticker, amount in self.resources.items()}
        return ResourceList(new_resources)

    def round(self):
        new_resources = {ticker: round(amount) for ticker, amount in self.resources.items()}
        return ResourceList(new_resources)

    def add(self, ticker, amount):
        add_list = None
        if isinstance(ticker, dict):
            add_list = ResourceList(ticker)
        if isinstance(ticker, ResourceList):
            add_list = ticker

        if add_list is not None:
            add_list = ResourceList(add_list)
            self += add_list
            return

        if ticker in self.resources:
            self.resources[ticker] += amount
        else:
            self.resources[ticker] = amount

    def subtract(self, ticker, amount):
        sub_list = None
        if isinstance(ticker, dict):
            sub_list = ResourceList(ticker)
        if isinstance(ticker, ResourceList):
            sub_list = ticker

        if sub_list is not None:
            sub_list = ResourceList(add_list)
            self -= add_list
            return

        if ticker in self.resources:
            self.resources[ticker] += amount
        else:
            self.resources[ticker] = amount

    def split(self):
        single_resources = []
        for ticker, amount in self.resources.items():
            single_resources.append(ResourceList({ticker: amount}))
        return single_resources

    def __add__(self, other):
        if not isinstance(other, ResourceList):
            return NotImplemented
        new_resources = self.resources.copy()
        for ticker, amount in other.resources.items():
            if ticker in new_resources:
                new_resources[ticker] += amount
            else:
                new_resources[ticker] = amount
        return ResourceList(new_resources)

    def __sub__(self, other):
        if not isinstance(other, ResourceList):
            return NotImplemented
        new_resources = self.resources.copy()

        for ticker, amount in other.resources.items():
            if ticker in new_resources:
                new_resources[ticker] -= amount
            else:
                new_resources[ticker] = -amount

        return ResourceList(new_resources)

    def __mul__(self, multiplier):
        if not isinstance(multiplier, int) and not isinstance(multiplier, float):
            return NotImplemented
        new_resources = {ticker: amount * multiplier for ticker, amount in self.resources.items()}
        return ResourceList(new_resources)

    def __rmul__(self, multiplier):
        return self.__mul__(multiplier)

    def __len__(self):
        return len(self.resources)

    def json(self):
        return json.dumps(self.resources, indent=2)

    def __str__(self):
        formatted_resources = []
        for name, count in self.resources.items():
            if abs(count - round(count)) < 0.0001:  # Check if count is within 4 decimal places of an integer
                formatted_resources.append(f"{int(round(count))} {name}")  # Display as an integer
            else:
                formatted_resources.append(f"{count:.2f} {name}")  # Display with 2 decimal places

        return ', '.join(formatted_resources)

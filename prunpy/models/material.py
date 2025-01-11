from prunpy.models.logistics import Container

class Material:

    def __new__(cls, rawdata_or_ticker):
        if isinstance(rawdata_or_ticker, Material):
            return rawdata_or_ticker  # Return the same instance if already Material

        if isinstance(rawdata_or_ticker, str):
            from prunpy.data_loader import loader
            return loader.materials[rawdata_or_ticker]  # Return the existing Material from loader

        # If we don't have an existing Material or ticker, create a new instance
        return super(Material, cls).__new__(cls)

    def __init__(self, rawdata):
        if isinstance(rawdata, dict):
            # Initialize the instance with rawdata only if not previously initialized
            self.ticker = rawdata['Ticker']
            self.rawname = rawdata['Name']
            self.hash = rawdata['MaterialId']
            self.weight = round(rawdata['Weight'], 2)
            self.volume = round(rawdata['Volume'], 2)
            self.category_name = rawdata['CategoryName'].title()
            self.category_hash = rawdata['CategoryId']
        else:
            # If rawdata is not a dict, avoid reinitialization
            pass

    @property
    def name(self):
        if self.__dict__.get('cached_name'): return self.cached_name

        import re
        s = self.rawname
        # Insert spaces before uppercase letters
        s = re.sub(r'([A-Z])', r' \1', s)
        # Insert spaces before sequences of digits
        s = re.sub(r'(\d+)', r' \1', s)
        # Remove any leading/trailing spaces
        s = s.strip()
        # Split into words and capitalize each
        words = s.split()
        words = [w.capitalize() for w in words]
        s = ' '.join(words)
        # Define replacements for exceptions
        replacements = {
            'Ftl': 'FTL',
            'Stl': 'STL',
            'Ai': 'AI',
            'Highg': 'High-G',
        }
        # Apply the replacements
        for key, value in replacements.items():
            s = s.replace(key, value)
        
        self.cached_name = s
        return s

    @property
    def category(self):
        return self.category_name

    @property
    def storage_ratio(self):
        if self.volume == 0:
            if self.weight == 0: return 1
            return float('inf')
        return round(self.weight / self.volume, 2)

    def get_value(self, exchange=None, trade_type="buy"):
        from prunpy.data_loader import loader 
        
        exchange = loader.get_exchange(exchange)

        if not isinstance(trade_type, str):
            return NotImplemented
        trade_type = trade_type.lower()

        if trade_type == "buy":
            return exchange.get_good(self.ticker).buy_price
        else: # trade_type == "sell" or other:
            return exchange.get_good(self.ticker).sell_price
            
    def get_color(self):
        from prunpy.constants import MATERIAL_CATEGORY_COLORS_BRIGHTENED as colors
        if self.category in colors:
            return colors[self.category]
        else:
            return '#AAAAAA'

    def __str__(self):

        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        r, g, b = hex_to_rgb(self.get_color())
        # ANSI escape code for bold text
        bold = "\033[1m"
        # Create ANSI escape code for the foreground color
        fg_color = f"\033[38;2;{r};{g};{b}m"
        # Reset code to end the styling
        reset = "\033[0m"

        return f"{bold}{fg_color}{self.ticker}{reset}"
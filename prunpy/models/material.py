from prunpy.models.logistics import Container

class Material:

    def __init__(self, rawdata_or_ticker):

        if isinstance(rawdata_or_ticker, str):
            rawdata = loader.materials[rawdata_or_ticker]
        else:
            rawdata = rawdata_or_ticker

        #self.rawdata = rawdata
        self.ticker = rawdata['Ticker']
        self.rawname = rawdata['Name']
        self.hash = rawdata['MaterialId']

        # Round weight and volume to 2 decimal places
        self.weight = round(rawdata['Weight'], 2)
        self.volume = round(rawdata['Volume'], 2)

        self.category_name_raw = rawdata['CategoryName']
        self.category_hash_raw = rawdata['CategoryId']

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
    def category_name(self):
        # Capitalize first letter of each word
        return self.category_name_raw.title()

    @property
    def storage_ratio(self):
        if self.volume == 0:
            if self.weight == 0: return 1
            return float('inf')
        return round(self.weight / self.volume, 2)

    def __str__(self):
        return self.ticker
from prunpy.data_loader import loader
import time



class PriceHistory:
    def __init__(self, material_ticker, exchange_ticker):
        self.material_ticker = material_ticker
        self.exchange_ticker = exchange_ticker

        self.rawdata = loader.get_exchange_price_history(exchange_ticker, material_ticker)

        rawintervals = {}
        for listing in self.rawdata:
            interval = listing['Interval']
            if interval not in rawintervals.keys():
                rawintervals[interval] = []
            rawintervals[interval].append(listing)

        self.intervals = {}
        for interval, listings in rawintervals.items():
            self.intervals[interval] = PriceHistoryInterval(material_ticker, exchange_ticker, interval, listings)

        # Reorder intervals by decreasing interval_ms
        self.intervals = dict(sorted(self.intervals.items(), key=lambda x: x[1].interval_ms, reverse=True))

    @property
    def average_traded_daily(self):
        if not self.intervals.get('DAY_ONE'):
            return 0
        return self.intervals['DAY_ONE'].average_traded

class PriceHistoryInterval:
    def __init__(self, material_ticker, exchange_ticker, interval_name, listings):
        self.material_ticker = material_ticker
        self.exchange_ticker = exchange_ticker
        self.interval_name = interval_name

        self.listings = listings
        # Sort listings by increasing DateEpochMs
        self.listings.sort(key=lambda x: x['DateEpochMs'])

        self.start_ms = self.listings[0]['DateEpochMs']
        self.end_ms = self.listings[-1]['DateEpochMs']
        self.span_ms = self.end_ms - self.start_ms

        interval_values = {
            "MINUTE_THIRTY": 30 * 60 * 1000,
            "MINUTE_FIFTEEN": 15 * 60 * 1000,
            "MINUTE_FIVE": 5 * 60 * 1000,
            "HOUR_ONE": 60 * 60 * 1000,
            "HOUR_FOUR": 4 * 60 * 60 * 1000,
            "HOUR_SIX": 6 * 60 * 60 * 1000,
            "HOUR_TWO": 2 * 60 * 60 * 1000,
            "HOUR_TWELVE": 12 * 60 * 60 * 1000,
            "DAY_ONE": 24 * 60 * 60 * 1000,
            "DAY_THREE": 3 * 24 * 60 * 60 * 1000
        }
        self.interval_ms = interval_values[self.interval_name] 

    @property
    def start_time(self):
        return convert_epoch_ms_to_readable(self.start_ms)

    @property
    def end_time(self):
        return convert_epoch_ms_to_readable(self.end_ms)

    @property
    def span(self):
        return convert_ms_to_readable(self.span_ms)

    @property
    def interval(self):
        return convert_ms_to_readable(self.interval_ms)

    @property
    def average_traded(self):
        return sum([listing['Traded'] for listing in self.listings]) / len(self.listings)

    def __len__(self):
        return len(self.listings)

def convert_ms_to_readable(ms):
    # Convert milliseconds to seconds
    seconds = ms / 1000

    # Use time.gmtime to convert seconds into a time structure
    time_struct = time.gmtime(seconds)

    # Extract days, hours, minutes, and seconds from the time structure
    days = time_struct.tm_yday - 1  # tm_yday is 1-based, so subtract 1
    hours = time_struct.tm_hour
    minutes = time_struct.tm_min
    remaining_seconds = time_struct.tm_sec

    #return f"{days}d {hours}h {minutes}m {remaining_seconds}s"

    # Build the readable format
    output = ""
    if days > 0:
        output += f"{days}d"
    if hours > 0:
        output += f"{hours}h"
    if minutes > 0:
        output += f"{minutes}m"
    if remaining_seconds > 0:
        output += f"{remaining_seconds}s"
    
    return output

def convert_epoch_ms_to_readable(epoch_timestamp):
    # Convert the Unix timestamp to a local time struct
    time_struct = time.localtime(epoch_timestamp)
    
    # Format the time struct into a human-readable format
    readable_time = time.strftime("%Y-%m-%d %H:%M:%S", time_struct)
    
    return readable_time
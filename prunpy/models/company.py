from prunpy.api import fio
import time
import json

"""
Note: company_identifier can be a company name, username, or to refresh existing instance of this class
- It can also use a company code, but these are NOT UNIQUE. Eg FISH yields a defunct company instead of fishnet fabrication
"""
class Company:
    def __init__(self, company_identifier):

        rawdata = self.get_company_data(company_identifier)

        self.username = rawdata.get('UserName')

        self.name = rawdata.get('CompanyName')
        self.code = rawdata.get('CompanyCode')
        self.ticker = self.code

        self.country_name = rawdata.get('CountryName')
        self.country_code = rawdata.get('CountryCode')
        self.country_ticker = self.country_code

        self.corporation_name = rawdata.get('CorporationName')
        self.corporation_code = rawdata.get('CorporationCode')
        self.corporation_ticker = self.corporation_code

        self.rating = rawdata.get('OverallRating')
        self.subscription = rawdata.get('SubscriptionLevel')
        self.created_timestamp = rawdata.get('CreatedEpochMs')
        # Convert to ISO formatted UTC creation time
        self.created_date_utc = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(self.created_timestamp/1000))

        self.planet_ids = [planet['PlanetNaturalId'] for planet in rawdata.get('Planets')]


    def get_company_data(self, company_identifier):
        
        # Get Identifier type
        if isinstance(company_identifier, Company):
            identifier_type = 'class'
        elif isinstance(company_identifier, str):
            if company_identifier.isupper() and len(company_identifier) <= 4:
                identifier_type = 'ticker'
            else:
                identifier_type = 'name'

        cache_time = 60*60*24 # 1 day

        # Get data
        if identifier_type == 'class':
            rawdata = fio.request("GET", f"/company/name/{company_identifier.name}", cache=cache_time)
        elif identifier_type == 'ticker':
            rawdata = fio.request("GET", f"/company/code/{company_identifier}", cache=cache_time)
        elif identifier_type == 'name':  # Could be username or company name
            try:
                rawdata = fio.request("GET", f"/company/name/{company_identifier}", cache=cache_time)
            except Exception as e:
                try:
                    rawdata = fio.request("GET", f"/user/{company_identifier}", cache=cache_time)
                except Exception as e:
                    raise ValueError(f"Failed to fetch company \"{company_identifier}\": {str(e)}")
        else:
            raise ValueError("Invalid identifier type")

        return rawdata


    def __repr__(self):
        return json.dumps(self.__dict__, indent=4)

    def __str__(self):
        return self.name
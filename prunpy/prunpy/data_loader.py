from prunpy.api import fio

from prunpy.constants import DEFAULT_BUILDING_PLANET_NATURAL_ID

class DataLoader:
    def __init__(self):
        self._cache = {}
        self.planet_dicts = {}

    def _get_cached_data(self, key):
        """Retrieve data from cache if available."""
        return self._cache.get(key)

    def _set_cache(self, key, data):
        """Store data in cache."""
        self._cache[key] = data
        return data

    @property
    def allplanets(self):
        cache_key = 'allplanets'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        allplanets = fio.request("GET", f"/planet/allplanets/full")
        return self._set_cache(cache_key, allplanets)

    @property
    def planet_lookup(self):
        cache_key = 'planet_lookup'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        planet_lookup = {planet['PlanetNaturalId']: planet for planet in self.allplanets}
        return self._set_cache(cache_key, planet_lookup)

    @property
    def system_planet_lookup(self):
        cache_key = 'system_planet_lookup'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        system_planet_lookup = {}
        for planet in self.allplanets:
            if planet['SystemId'] not in system_planet_lookup:
                system_planet_lookup[planet['SystemId']] = []
            system_planet_lookup[planet['SystemId']].append(planet['PlanetName'])
        return self._set_cache(cache_key, system_planet_lookup)

    @property
    def rawsystemstars(self):
        cache_key = 'rawsystemstars'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        rawsystemstars = fio.request("GET", f"/systemstars")
        return self._set_cache(cache_key, rawsystemstars)

    @property
    def systemstars_lookup(self):
        cache_key = 'systemstars_lookup'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        systemstars_lookup = {system["SystemId"]: system for system in self.rawsystemstars}
        return self._set_cache(cache_key, systemstars_lookup)

    @property
    def allmaterials(self):
        cache_key = 'allmaterials'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        allmaterials = fio.request("GET", "/material/allmaterials")
        # Remove the entry with ticker "CMK", as it's not craftable
        for i in range(len(allmaterials)):
            if allmaterials[i]['Ticker'] == 'CMK':
                del allmaterials[i]
                break
        return self._set_cache(cache_key, allmaterials)

    @property
    def materials_by_ticker(self):
        cache_key = 'materials_by_ticker'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        materials_by_ticker = {material['Ticker']: material for material in self.allmaterials}
        return self._set_cache(cache_key, materials_by_ticker)

    @property
    def material_ticker_list(self):
        cache_key = 'material_ticker_list'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        return self._set_cache(cache_key, self.materials_by_ticker.keys())

    def get_material(self, ticker):
        cache_key = 'get_material_' + str(ticker)
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        material = self.materials_by_ticker[ticker]
        return self._set_cache(cache_key, material)

    @property
    def materials_by_hash(self):
        cache_key = 'material_by_hash'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        materials_by_hash = {material['MaterialId']: material for material in self.allmaterials}
        return self._set_cache(cache_key, materials_by_hash)

    @property
    def allbuildings_raw(self):
        cache_key = 'allbuildings_raw'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        allbuildings_raw = fio.request("GET", f"/building/allbuildings", cache=-1)
        return self._set_cache(cache_key, allbuildings_raw)

    @property
    def rawexchangedata(self):
        cache_key = 'rawexchangedata'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        rawexchangedata = fio.request("GET", f"/exchange/full", message="Fetching exchange data...")
        return self._set_cache(cache_key, rawexchangedata)

    @property
    def rawexchanges(self):
        cache_key = 'rawexchanges'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        rawexchanges = fio.request("GET", "/exchange/station", cache='forever')
        return self._set_cache(cache_key, rawexchanges)


    @property
    def all_population_reports(self):
        cache_key = 'all_population_reports'
        if (cached_data := self._get_cached_data(cache_key)) is not None: return cached_data

        all_population_reports_raw = fio.request("GET", "/csv/infrastructure/allreports", cache=60*60*24)
        all_population_reports = {}
        for report in all_population_reports_raw:
            planet_id = report["PlanetNaturalId"]
            # Initialize the list for this planet if it doesn't exist
            if planet_id not in all_population_reports:
                all_population_reports[planet_id] = []
            all_population_reports[planet_id].append(report)
        return self._set_cache(cache_key, all_population_reports)

loader = DataLoader()

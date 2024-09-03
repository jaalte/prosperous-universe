from prunpy.utils.resource_list import ResourceList

# Constants
EXTRACTORS = {
    'COL': {
        'ticker': 'COL',
        'type': 'GASEOUS',
        'cycle_time': 6, # hours per cycle
        'multiplier': 0.6,
    },
    'RIG': {
        'ticker': 'RIG',
        'type': 'LIQUID',
        'cycle_time': 4.8,
        'multiplier': 0.7,
    },
    'EXT': {
        'ticker': 'EXT',
        'type': 'MINERAL',
        'cycle_time': 12,
        'multiplier': 0.7,
    },
}

PLANET_THRESHOLDS = {
    'temperature': (-25, 75),
    'pressure': (0.25, 2),
    'gravity': (0.25, 2.5),
}

DISTANCE_PER_PARSEC = 12
STL_FUEL_FLOW_RATE = 0.015 # Unknown what it means but it's from /ship/ships/fishmodem
# Pretty sure its a factor of distance, not time:
# - Cause even in close STL transfers in Montem, fuel cost is ~107

DEMOGRAPHICS =  ["pioneers", "settlers", "technicians", "engineers", "scientists"]
POPULATION_UPKEEP_PER_100_PER_DAY = {
    'pioneers':    ResourceList({'RAT': 4, 'DW': 4,   'OVE': 0.5,                         'PWO': 0.2, 'COF': 0.5}),
    'settlers':    ResourceList({'RAT': 6, 'DW': 5,   'EXO': 0.5, 'PT':  0.5,             'REP': 0.2, 'KOM': 1  }),
    'technicians': ResourceList({'RAT': 7, 'DW': 7.5, 'MED': 0.5, 'HMS': 0.5, 'SCN': 0.1, 'SC':  0.1, 'ALE': 1  }),
    'engineers':   ResourceList({'FIM': 7, 'DW': 10,  'MED': 0.5, 'HSS': 0.2, 'PDA': 0.1, 'VG':  0.2, 'GIN': 1  }),
    'scientists':  ResourceList({'MEA': 7, 'DW': 10,  'MED': 0.5, 'LC':  0.2, 'WS':  0.1, 'NS':  0.1, 'WIN': 1  }),
}

# Tacotopia, no resources, no harsh environment, no fertility, has surface (MCG)
#   also has population and resource_extraction cogc lol
DEFAULT_BUILDING_PLANET_NATURAL_ID = "CB-045b"

BOGUS_ORDER_THRESHOLD = 5

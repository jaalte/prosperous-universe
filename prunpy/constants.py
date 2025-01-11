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

# Available from /global/simulationdata['ParsecLength']
# Also available, but less obviously useful: "SimulationInterval": 86400, "FlightSTLFactor": 1, "FlightFTLFactor": 1, "PlanetaryMotionFactor": 20,
DISTANCE_PER_PARSEC = 12

STL_FUEL_FLOW_RATE = 0.015 # Unknown what it means but it's from /ship/ships/fishmodem
# Pretty sure its a factor of distance, not time:
# - Cause even in close STL transfers in Montem, fuel cost is ~107

DEMOGRAPHICS =  ["pioneers", "settlers", "technicians", "engineers", "scientists"]

BASIC_HOUSING_BUILDINGS = {
    'pioneers': 'HB1',
    'settlers': 'HB2',
    'technicians': 'HB3',
    'engineers': 'HB4',
    'scientists': 'HB5',
}

HOUSING_SIZES = {
    'HB1': {
        'pioneers': 100,
    },
    'HB2': {
        'settlers': 100,
    },
    'HB3': {
        'technicians': 100,
    },
    'HB4': {
        'engineers': 100,
    },
    'HB5': {
        'scientists': 100,
    },
    'HBB': {
        'pioneers': 75,
        'settlers': 75,
    },
    'HBC': {
        'settlers': 75,
        'technicians': 75,
    },
    'HBM': {
        'technicians': 75,
        'engineers': 75,
    },
    'HBL': {
        'engineers': 75,
        'scientists': 75,
    },
}

# Moved to prunpy.loader.get_population_upkeep()
# POPULATION_UPKEEP_PER_100_PER_DAY = {
#     'pioneers':    ResourceList({'RAT': 4, 'DW': 4,   'OVE': 0.5,                         'PWO': 0.2, 'COF': 0.5}),
#     'settlers':    ResourceList({'RAT': 6, 'DW': 5,   'EXO': 0.5, 'PT':  0.5,             'REP': 0.2, 'KOM': 1  }),
#     'technicians': ResourceList({'RAT': 7, 'DW': 7.5, 'MED': 0.5, 'HMS': 0.5, 'SCN': 0.1, 'SC':  0.1, 'ALE': 1  }),
#     'engineers':   ResourceList({'FIM': 7, 'DW': 10,  'MED': 0.5, 'HSS': 0.2, 'PDA': 0.1, 'VG':  0.2, 'GIN': 1  }),
#     'scientists':  ResourceList({'MEA': 7, 'DW': 10,  'MED': 0.5, 'LC':  0.2, 'WS':  0.1, 'NS':  0.1, 'WIN': 1  }),
# }

COGCS = ['FUEL_REFINING', 'FOOD_INDUSTRIES', 'METALLURGY', 'AGRICULTURE', 'CHEMISTRY', 'RESOURCE_EXTRACTION', 'ELECTRONICS', 'CONSTRUCTION', 'MANUFACTURING', 'PIONEERS', 'SETTLERS', 'TECHNICIANS', 'ENGINEERS', 'SCIENTISTS']

# Tacotopia, no resources, no harsh environment, no fertility, has surface (MCG)
#   also has population and resource_extraction cogc lol
DEFAULT_BUILDING_PLANET_NATURAL_ID = "CB-045b"

BOGUS_ORDER_THRESHOLD = 5

MATERIAL_CATEGORY_COLORS = {
    "Agricultural Products": "#005500",  # RSI
    "Alloys": "#8B5C2F",  # AST
    "Chemicals": "#C63E6A",  # TCL
    "Construction Materials": "#286BE4",  # SEA
    "Construction Parts": "#375A78",  # AEF
    "Construction Prefabs": "#1E2E71",  # RBH
    "Consumables (Basic)": "#B23336",  # DW
    "Consumables (Luxury)": "#73000A",  # KOM
    "Drones": "#606830",  # CCD
    "Electronic Devices": "#6725A5",  # BSC
    "Electronic Parts": "#693DC5",  # MB
    "Electronic Pieces": "#8660CB",  # BCO
    "Electronic Systems": "#402658",  # ACS
    "Elements": "#4C3D30",  # TC
    "Energy Systems": "#234D36",  # CBL
    "Fuels": "#609931",  # FF
    "Gases": "#117B7D",  # AMM
    "Liquids": "#629FCC",  # BTS
    "Medical Equipment": "#64B964",  # ADR
    "Metals": "#4B4B4B",  # CU
    "Minerals": "#A87F57",  # BOR
    "Ores": "#60656F",  # LIO
    "Plastics": "#8A3072",  # DCL
    "Ship Engines": "#AB3C12",  # AEN
    "Ship Kits": "#A9630F",  # LCB
    "Ship Parts": "#AA7411",  # SSC
    "Ship Shields": "#EF920E",  # APT
    "Software Components": "#9A8B41",  # BAI
    "Software Systems": "#4C4413",  # IMM
    "Software Tools": "#8C6C1D",  # DA
    "Textiles": "#616931",  # CF
    "Unit Prefabs": "#333132",  # CQS
    "Utility": "#AFA397"  # UTS
}

MATERIAL_CATEGORY_COLORS_BRIGHTENED = {
    "Agricultural Products": "#008a00",
    "Alloys": "#a56d37",
    "Chemicals": "#c63e6a",
    "Construction Materials": "#286be4",
    "Construction Parts": "#47749b",
    "Construction Prefabs": "#283d98",
    "Consumables (Basic)": "#b83438",
    "Consumables (Luxury)": "#99000d",
    "Drones": "#889344",
    "Electronic Devices": "#6f27b2",
    "Electronic Parts": "#683dc5",
    "Electronic Pieces": "#855fcb",
    "Electronic Systems": "#653c8b",
    "Elements": "#856b54",
    "Energy Systems": "#3c865e",
    "Fuels": "#6cac37",
    "Gases": "#159b9e",
    "Liquids": "#619fcc",
    "Medical Equipment": "#65bc65",
    "Metals": "#858585",
    "Minerals": "#b3875d",
    "Ores": "#828997",
    "Plastics": "#a43987",
    "Ship Engines": "#b53f13",
    "Ship Kits": "#b4690f",
    "Ship Parts": "#b47b12",
    "Ship Shields": "#ef920e",
    "Software Components": "#ac9b48",
    "Software Systems": "#857721",
    "Software Tools": "#a57f22",
    "Textiles": "#889445",
    "Unit Prefabs": "#797476",
    "Utility": "#b7aa9e"
}


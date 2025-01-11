# prunpy/__init__.py

from .api import fio
from .api import fio as api
from .data_loader import loader

# Import key classes from the models package
from .models.planet import Planet
from .models.system import System
from .models.base import Base, RealBase
from .models.building import Building
from .models.exchange import Exchange
from .models.price_history import PriceHistory
from .models.recipe import Recipe
from .models.recipe_queue import RecipeQueue, RecipeQueueItem
from .models.population import Population
from .models.company import Company
from .models.material import Material
from .models.logistics import Container
from .models import pathfinding
from .utils.resource_list import ResourceList
from .utils.building_list import BuildingList
from .utils.terminal_formatting import terminal_color_scale
from .utils.terminal_formatting import terminal_format

# Import utility functions
# from .utils import threshold_round, distance

# Define the public API of the package
__all__ = [
    'fio', 'loader',
    'Planet', 'System', 'Base', 'RealBase', 'Building',
    'Exchange', 'PriceHistory', 'Recipe', 'RecipeQueue', 'RecipeQueueItem',
    'ResourceList', 'BuildingList', 'Population',
    'Container', 'Material', 'Company',
    'terminal_color_scale', 'terminal_format',
    
    'pathfinding', # Deprecated
]

from prunpy.utils.resource_list import ResourceList
from prunpy.constants import DEMOGRAPHICS
from prunpy.data_loader import loader

class Population:
    def __init__(self, population_dict):
        # TODO: Implement parsing of multiple rawdata types to clean up code elsewhere
        if isinstance(population_dict, Population):
            self.population = population_dict.population
        elif isinstance(population_dict, dict):
            self.population = population_dict

        # Add keys set to 0 for all in DEMOGRAPHICS 
        for demographic in DEMOGRAPHICS:
            if demographic not in self.population:
                self.population[demographic] = 0
        

    def get_upkeep(self):
        # Population is a dict of {demographic: amount}
        needs = ResourceList()
        for demographic in self.population:
            needs += self.population[demographic]/100 * loader.get_population_upkeep()[demographic]
        return needs.prune()

    @property
    def upkeep(self):
        return self.get_upkeep()

    @property
    def pioneers(self):
        return self.population.get('pioneers', 0)

    @property
    def settlers(self):
        return self.population.get('settlers', 0)

    @property
    def technicians(self):
        return self.population.get('technicians', 0)

    @property
    def engineers(self):
        return self.population.get('engineers', 0)

    @property
    def scientists(self):
        return self.population.get('scientists', 0)

    def get_demographic(self, demographic):
        demographic = demographic.lower()
        
        # If last character is not "s", add "s"
        if demographic[-1] != 's' and demographic[-1] != 'S':
            demographic = demographic + 's'

        if not demographic in self.population:
            raise KeyError(f"Population.get called for unknown demographic: {demographic}")
        return self.population[demographic]

    def get(self, demographic):
        if not demographic in self.population:
            raise KeyError(f"Population.get called for unknown demographic: {demographic}")
        return self.population[demographic]

    def get_housing_needs(self, priority='cost'):
        from prunpy.utils.building_list import BuildingList
        from prunpy.constants import BASIC_HOUSING_BUILDINGS
        if priority == 'area':
            pass

        # Priority is cost
        housing = BuildingList()
        for demographic, count in self.population.items():
            housing += BuildingList({
                BASIC_HOUSING_BUILDINGS[demographic]: count/100
            })

        return housing.prune()


    #def __getitem__(self, demographic):
    #    return self.population.get(demographic.lower(), 0)

    def __add__(self, other):
        if not isinstance(other, Population):
            return NotImplemented
        result_population = {}
        for demographic, amount in self.population.items():
            result_population[demographic] = amount + other.population.get(demographic, 0)
        for demographic, amount in other.population.items():
            if demographic not in result_population:
                result_population[demographic] = amount
        return Population(result_population)

    def __sub__(self, other):
        if not isinstance(other, Population):
            return NotImplemented
        result_population = {}
        for demographic, amount in self.population.items():
            result_population[demographic] = amount - other.population.get(demographic, 0)
        return Population(result_population)

    def __mul__(self, factor):
        if not isinstance(factor, (int, float)):
            return NotImplemented
        result_population = {demographic: amount * factor for demographic, amount in self.population.items()}
        return Population(result_population)

    __rmul__ = __mul__  # Allows multiplication with a float on the left-hand side

    def __iter__(self):
        return self.population.items()

    def __str__(self):
        return str(self.population)

from prunpy.utils.resource_list import ResourceList
from prunpy.constants import POPULATION_UPKEEP_PER_100_PER_DAY

class Population:
    def __init__(self, population_dict):
        # TODO: Implement parsing of multiple rawdata types to clean up code elsewhere
        self.population = population_dict

    def get_upkeep(self):
        # Population is a dict of {demographic: amount}
        needs = ResourceList()
        for demographic in self.population:
            needs += self.population[demographic]/100 * POPULATION_UPKEEP_PER_100_PER_DAY[demographic]
        return needs

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

    def __getitem__(self, demographic):
        return self.population.get(demographic.lower(), 0)

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

    def __str__(self):
        return str(self.population)

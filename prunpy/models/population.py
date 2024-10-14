from prunpy.utils.resource_list import ResourceList
from prunpy.constants import DEMOGRAPHICS, DEFAULT_BUILDING_PLANET_NATURAL_ID
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

    @property
    def total(self):
        return sum(self.population.values())

    def get_demographic(self, demographic):
        demographic = demographic.lower()
        
        # If last character is not "s", add "s"
        if demographic[-1] != 's' and demographic[-1] != 'S':
            demographic = demographic + 's'

        if not demographic in self.population:
            raise KeyError(f"Population.get called for unknown demographic: {demographic}")
        return self.population[demographic]

    def get(self, demographic, default=0):
        if not demographic in self.population:
            return default
        return self.population[demographic]


    # Note: Assumes NC1, on a rocky planet with no modifiers
    # Since housing costs are relative, this shouldn't matter much
    def get_housing_needs(self, priority='cost', planet=None):
        from prunpy.utils.building_list import BuildingList
        from scipy.optimize import linprog

        if priority not in ['cost', 'area']:
            raise KeyError(f"Population.get_housing_needs called with unknown priority: {priority}")

        if planet is None:
            planet = loader.get_planet(DEFAULT_BUILDING_PLANET_NATURAL_ID)
        else:
            planet = loader.get_planet(planet)

        exchange_code = 'NC1'  # Should be representative across all exchanges
        target = self.invert()

        # Retrieve housing buildings and their associated costs and areas
        housing_tickers = ['HB1', 'HB2', 'HB3', 'HB4', 'HB5', 'HBB', 'HBC', 'HBM', 'HBL']
        housing_objects = BuildingList({
            ticker: 1 for ticker in housing_tickers
        }, planet=planet).get_building_instances()

        # Prepare the optimization matrix for scipy.optimize.linprog
        # The objective is to minimize either cost or area
        if priority == 'cost':
            c = [building.get_cost(exchange_code) for building in housing_objects]  # Minimize cost
        else:
            c = [building.area for building in housing_objects]  # Minimize area

        # Debugging: Print objective function coefficients
        #print("Objective function coefficients (c):", c)

        # Coefficients for the inequality constraints
        A = []
        b = []

        # For each demographic in DEMOGRAPHICS, create a constraint
        for demographic in DEMOGRAPHICS:
            demographic_housing = [building.population_demand.get(demographic, 0) for building in housing_objects]
            total_required_housing = -self.get(demographic)  # The total required housing for this demographic

            # Debugging: Print constraint row and required housing
            #print(f"Demographic: {demographic}, Housing constraint row: {demographic_housing}, Total required housing: {total_required_housing}")

            A.append(demographic_housing)
            b.append(total_required_housing)

        # Set bounds (no negative buildings, so minimum is 0)
        bounds = [(0, None) for _ in housing_objects]

        # Debugging: Print constraints matrix and bounds
        #print("Inequality constraints matrix (A):", A)
        #print("Constraints vector (b):", b)
        #print("Bounds:", bounds)

        # Solve the linear programming problem using scipy's linprog
        result = linprog(
            c,                  # Objective function coefficients (cost or area)
            A_ub=A,             # Coefficients for inequality constraints (housing)
            b_ub=b,             # Total required housing for each demographic
            bounds=bounds,      # Bound constraints (min 0, no max limit)
            method='highs'      # Using the recommended method
        )

        # Debugging: Check the result status
        #print("Optimization result:", result)

        if result.success:
            # Return the optimized number of buildings needed
            optimal_solution = result.x
            need = {housing_objects[i].ticker: float(optimal_solution[i]) for i in range(len(housing_objects))}
            return BuildingList(need, planet).prune()
        else:
            raise ValueError("Optimization failed. Please check the inputs and constraints.")



            
    #def __getitem__(self, demographic):
    #    return self.population.get(demographic.lower(), 0)

    def invert(self):
        return Population({demographic: -amount for demographic, amount in self.population.items()})

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

from prunpy.data_loader import loader

class RecipeTreeNode:
    def __init__(self, recipe, depth=0, multiplier=1, priority_mode='profit_ratio', include_worker_upkeep=False):
        self.recipe = recipe
        self.depth = depth
        self.multiplier = multiplier
        self.priority_mode = priority_mode
        self.include_worker_upkeep = include_worker_upkeep

        self.children = {}

        for input_ticker in self.recipe.inputs.tickers:
            #print(input_ticker)
            recipes = loader.get_material_recipes(input_ticker, 
                include_mining_from_planet_id='XG-326a',
                #include_purchase_from='NC1'
            )
            recipes = self.sort_recipes(recipes, priority_mode)



            need = self.recipe.inputs.resources[input_ticker] * self.multiplier
            
            for recipe in recipes:
                #print(recipe)
                provided = recipe.outputs.resources[input_ticker]
                new_child_multiplier = need / provided

                self.children[input_ticker] = RecipeTreeNode(
                    recipe=recipe,
                    depth=self.depth + 1,
                    multiplier=new_child_multiplier,
                    priority_mode=self.priority_mode,
                    include_worker_upkeep=self.include_worker_upkeep
                )

    def __mul__(self, multiplier):
        if not isinstance(multiplier, int) and not isinstance(multiplier, float):
            return NotImplemented

        newself = self.copy()
        newself.recipe = self.recipe.copy()
        newself.recipe.duration *= multiplier
        newself.recipe.inputs *= multiplier
        newself.recipe.outputs *= multiplier
        newself.recipe.multiplier = newself.recipe.multiplier or 1
        newself.recipe.multiplier *= multiplier

        return newself

    def __rmul__(self, multiplier):
        return self.__mul__(multiplier)

    @property
    def has_children(self):
        return len(self.children) > 0

    @property
    def isterminal(self):
        return not self.has_children

    def sort_recipes(self, recipes, priority_mode):
        if priority_mode == 'throughput':
            return sorted(recipes, key=lambda x: x.throughput, reverse=True)
        elif priority_mode == 'profit_amount':
            return sorted(recipes, key=lambda x: x.get_profit_per_hour('NC1'), reverse=True)
        elif priority_mode == 'profit_ratio':
            return sorted(recipes, key=lambda x: x.get_profit_ratio('NC1'), reverse=True)
        else:
            raise ValueError(f"Invalid priority mode: {priority_mode}")

    def get_total_inputs(self, include_worker_upkeep=False):
        inputs = self.recipe.inputs * self.multiplier
        for child in self.children:
            inputs += child.get_total_inputs(include_worker_upkeep)
        return inputs

    def get_total_outputs(self, include_worker_upkeep=False):
        outputs = self.recipe.outputs * self.multiplier
        for child in self.children:
            outputs += child.get_total_outputs(include_worker_upkeep)
        return outputs

    def __str__(self):
        string = "| " * self.depth + str(self.recipe)
        for material_ticker, child in self.children.items():
            string += "\n" + child.__str__()
        return string



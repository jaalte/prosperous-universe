from prunpy.game_importer import importer



class RecipeTreeRoot:
    def __init__(self, root_ticker, priority_mode):
        self.root_ticker = root_ticker
        self.priority_mode = priority_mode

        # Populate children
        self.children = importer.get_material_recipes(root_ticker)

        

   



    def get_single_recipe_string(self, recipe):
        return f"{recipe.outputs} <= {recipe.inputs} in {recipe.duration:.1f}h @ {recipe.building}"



class RecipeTreeNode:
    def __init__(self, recipe):
        self.recipe = recipe
        self.children = []
        self.multiplier = 1
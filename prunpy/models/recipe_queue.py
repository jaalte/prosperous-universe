import numpy as np
import math
from prunpy.data_loader import loader
from prunpy.models.recipe import Recipe
from prunpy.utils.resource_list import ResourceList



struct = []

class RecipeQueue:
    def __init__(self, capacity=5):
        self.capacity = capacity
        self.queue = []
    
    @property
    def free_slots(self):
        return self.capacity - len(self.queue)

    def used_slots(self):
        return len(self.queue)

    def __len__(self):
        return len(self.queue)

    def queue_recipe(self, recipe, order_size=1, recurring=False):
        if self.free_slots == 0:
            raise OverflowError
        if not isinstance(recipe, Recipe):
            raise TypeError
        if not isinstance(order_size, int) and not isinstance(order_size, float):
            raise TypeError

        new_item = RecipeQueueItem(recipe, order_size=order_size, recurring=recurring)
        self.queue.append(new_item)
        return self

    def queue_recipe_item(self, item):
        if self.free_slots == 0:
            raise OverflowError
        if not isinstance(item, RecipeQueueItem):
            raise TypeError
        self.queue.append(item)
        return self

    @property
    def unique_recipes(self):
        # Returns a list of all recipes in the queue
        # Don't include duplicates
        all_recipes = [item.recipe for item in self.queue]
        return list(set(all_recipes))

    def clear(self):
        self.queue = []

    def balance(self, max_order_size=3, priority='daily_traded', exchange=None):
        recipe_ratios = self._calc_output_ratios_traded(exchange)
        new_queue = self._apply_queue_ratios(recipe_ratios, max_order_size)
        self.queue = new_queue
        return self

        
    def _calc_output_ratios_traded(self, exchange):
        exchange = loader.get_exchange(exchange)

        recipe_data = []

        ### 1. Prep data for ratio calculation
        for recipe in self.unique_recipes:
            # Temp, picks first output item
            # Use a method to pick most profitable later
            best_output = list(recipe.outputs.resources.keys())[0]

            good = exchange.get_good(best_output)
            daily_traded = good.daily_traded

            daily_produced = recipe.daily.outputs.resources[best_output]

            if best_output == 'HMS':
                daily_traded = 1000

            daily_saturation = daily_produced / daily_traded
            base_production_target = 1/daily_saturation

            recipe_data.append({
                'recipe': recipe,
                'output_ticker': best_output,
                'daily_traded': daily_traded,
                'daily_saturation': daily_saturation,
                'base_production_target': base_production_target,
            })


        # Normalize the production quantities
        total_saturation = sum([item['base_production_target'] for item in recipe_data])
        for data in recipe_data:
            data['ratio'] = data['base_production_target'] / total_saturation
            #print(f"{data['recipe']}: {data['ratio']}")

        recipe_ratios = {}
        for data in recipe_data:
            recipe_ratios[data['recipe']] = data['ratio']
        

        return recipe_ratios


    def _apply_queue_ratios(self, recipe_ratios, max_order_size):

        best_queue = []
        for recipe in self.unique_recipes:
            initial_queue_entry = {
                'recipe': recipe,
                'order_size': 1,
                'max_size': max_order_size
            }
            best_queue.append(initial_queue_entry)

        done = False
        while not done:

            reserved_slot_count = sum([slot['max_size'] for slot in best_queue])

            max_total_slots = self.capacity * max_order_size
            remaining_capacity = max_total_slots - reserved_slot_count 

            # Populate options for next queue
            next_queue_candidates = []
            for i, slot in enumerate(best_queue):
                other_slots = best_queue[:i] + best_queue[i+1:]

                # If there's room to grow in the slot
                if slot['order_size'] < slot['max_size']:
                    increased_slot = slot.copy()
                    increased_slot['order_size'] += 1
                # If there's no room in the slot but room for another slot
                elif remaining_capacity >= max_order_size:                    
                    increased_slot = slot.copy()
                    increased_slot['order_size'] += 1
                    increased_slot['max_size'] += max_order_size
                # If there's no room for any increase
                else:
                    continue

                next_queue_candidate = [increased_slot]
                next_queue_candidate += other_slots
                next_queue_candidates.append(next_queue_candidate)


            # for candidate in next_queue_candidates:
            #     distance = self._calc_ratio_distance(candidate, recipe_ratios)
            #     print(f"Candidate with distance {distance:.2%}:")
            #     for slot in candidate:
            #         print(f"  Recipe: {slot['recipe']}, Order Size: {slot['order_size']}, Max Size: {slot['max_size']}")
            #     print()

            if len(next_queue_candidates) > 0:
                best_candidate = best_queue
                current_best_distance = self._calc_ratio_distance(best_candidate, recipe_ratios)
                best_candidate_distance = current_best_distance
                for candidate in next_queue_candidates:
                    distance = self._calc_ratio_distance(candidate, recipe_ratios)
                    if distance < best_candidate_distance:
                        best_candidate = candidate
                        best_candidate_distance = distance
                    elif distance == best_candidate_distance:
                        # Ideally pick the simpler one
                        # But that's tough to quantify
                        pass
                
                if best_candidate_distance == current_best_distance:
                    done = True
                
                # print(f"New best entry with distance {best_candidate_distance:.2%}:")
                # for entry in best_candidate:
                #    print(f"  Recipe: {entry['recipe']}, Order Size: {entry['order_size']}/{entry['max_size']}")
                # print()

                best_queue = best_candidate
            else:
                done = True
                break

        # print(f"Final queue with distance {self._calc_ratio_distance(best_queue, recipe_ratios):.2%}:")
        # for entry in best_queue:
        #     print(f"  Recipe: {entry['recipe']}, Order Size: {entry['order_size']}/{entry['max_size']}")
        # print()

        # Split oversized slots into individual slots
        new_queue = []
        for slot in best_queue:
            if slot['max_size'] > max_order_size:
                denominator = slot['max_size'] // max_order_size
                quotient = slot['order_size'] // denominator
                remainder = slot['order_size'] % denominator
                parts = [quotient]*denominator
                for i in range(remainder):
                    parts[i] += 1
                for part in parts:
                    item = RecipeQueueItem(slot['recipe'], order_size=part, recurring=True)
                    new_queue.append(item)
            else:
                item = RecipeQueueItem(slot['recipe'], order_size=slot['order_size'], recurring=True)
                new_queue.append(item)

        return new_queue


    def _calc_ratio_distance(self, trial_queue, recipe_ratios):
        # Extract the total order size from trial_queue
        total_order_size = sum(slot['order_size'] for slot in trial_queue)

        # Normalize the trial_queue values similarly to recipe_ratios
        trial_ratios = {}
        for slot in trial_queue:
            recipe = slot['recipe']
            order_size = slot['order_size']
            trial_ratios[recipe] = order_size / total_order_size
        
        # Calculate the distance between trial_ratios and recipe_ratios
        distance = 0.0
        for recipe, ideal_ratio in recipe_ratios.items():
            trial_ratio = trial_ratios.get(recipe, 0.0)  # default to 0.0 if recipe is missing
            # Squared difference for distance calculation
            distance += (ideal_ratio - trial_ratio) ** 2
        
        # Return the square root of the sum of squared differences (Euclidean distance)
        return math.sqrt(distance)

    def copy(self):
        new_queue = RecipeQueue(capacity=self.capacity)
        new_queue.queue = [item.copy() for item in self.queue]
        return new_queue

    def __str__(self):
        out = f"Recipe Queue:\n"
        for slot in self.queue:
            out += f"  {slot}\n"
        return out

class RecipeQueueItem:
    def __init__(self, recipe, order_size=1, recurring=False, progress=0):
        if not isinstance(recipe, Recipe):
            raise TypeError
        if not isinstance(order_size, int) and not isinstance(order_size, float):
            raise TypeError
        
        self.recipe = recipe
        self.order_size = order_size
        self.recurring = recurring
        self.progress = 0

    def copy(self):
        return RecipeQueueItem(self.recipe, self.order_size, self.recurring)

    def __str__(self):
        multiplied_recipe = self.recipe.order_size_multiply(self.order_size)
        return f"[RecipeQueueItem {multiplied_recipe} (x{self.order_size}), {"Recurring" if self.recurring else "Non-recurring"}]"
from collections import OrderedDict

from auspex.policies.base import Policy


class LRU(Policy):

    name = "lru" #belongs to the class 
    

    def __init__(self , capacity : int):
        super().__init__(capacity)
        self.structure = OrderedDict()

    def get(self , key: int) -> bool:

        # if its a hit then move the key to the most recently used 
        # here that is the back of the dict assume it as a queue 
        if key in self.structure:
            self.structure.move_to_end(key)
            return True 

        # if the key is not found then simply return false 
        else:
            return False 

    def put(self , key: int) -> None:

        # if key is already in the dict then move it to recently used which is at 
        # the back of the dict assume it as a queue 
        if key in self.structure:
            self.structure.move_to_end(key)

        # if the queue is full evict the item present in the first index here that is the element 
        # which is not used recently at all
        elif len(self.structure) >= self.capacity: #>= instead of == is cuz of fail safe cuz like just in case you know
            self.structure.popitem(last = False)
            self.structure[key] = True 

        # if the queue is not full simply insert the key
        else: 
            self.structure[key] = True 
            
            

        
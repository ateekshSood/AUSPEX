from collections import OrderedDict

from auspex.policies.base import Policy


class LFU(Policy):

    name = "lfu"

    def __init__(self , capacity : int):
        super().__init__(capacity)
        self.url_count_map_structure = {}
        self.count_map_url_ordered_list = {}
        self.min_count = -1

    def add_to_ordered_dict(self , key : int , new_count : int) -> None:

        if new_count not in self.count_map_url_ordered_list:
            self.count_map_url_ordered_list[new_count] = OrderedDict()
            
        self.count_map_url_ordered_list[new_count][key] = None


    def key_in_map_handle(self , key : int) -> None:
        
        old_count = self.url_count_map_structure[key]
        ordered_list_of_old_count = self.count_map_url_ordered_list[old_count]
    
        del ordered_list_of_old_count[key]

        if not ordered_list_of_old_count :
            del self.count_map_url_ordered_list[old_count]

            if old_count == self.min_count:
                self.min_count +=1 

        
        self.url_count_map_structure[key] +=1

        new_count = self.url_count_map_structure[key]

    
        self.add_to_ordered_dict(key , new_count) 
        

    def get(self , key : int) -> bool:

        if key in self.url_count_map_structure:
            
            self.key_in_map_handle(key)
            
            return True 

        else:
            return False 


    def put(self , key : int) -> None:

        if key in self.url_count_map_structure:

            self.key_in_map_handle(key)
            

        elif len(self.url_count_map_structure) >= self.capacity:

            url_remove , _ = self.count_map_url_ordered_list[self.min_count].popitem(last = False)
            del self.url_count_map_structure[url_remove]

            if not self.count_map_url_ordered_list[self.min_count]:
                del self.count_map_url_ordered_list[self.min_count] 

            self.url_count_map_structure[key] = 1 
            self.min_count = 1

      
            self.add_to_ordered_dict(key , self.min_count)

         
        else:
            
            self.url_count_map_structure[key] = 1
            self.min_count = 1

            
            self.add_to_ordered_dict(key , self.min_count)


        
            
    
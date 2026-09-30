import heapq
from typing import NamedTuple

import numpy as np

from auspex.policies.base import Policy


class HeapStore(NamedTuple):
    next_use : int 
    key : int

class Belady(Policy):

    name = "belady"
    
    def __init__(self , capacity : int , trace_url : np.ndarray):

        super().__init__(capacity=capacity)
        self.position_counter = 0 
        self.cache_dict = {}
        self.heap = []
        self.curr = None
        self.next_use_arr = self.backward_pass(key_arr=trace_url)
        

        
    def backward_pass(self , key_arr : np.ndarray) -> np.ndarray:
        next_use = np.zeros(len(key_arr) , dtype=np.int32)
        visited_keys = {}
        len_key = len(key_arr)
        
        for i in range(len_key -1 , -1 , -1):
    
    # anohter one of my shitty attempts lol
    
    #         if key_arr[i] not in visited_keys:
    #             visited_keys[key_arr[i]] =  i
    #             next_use[i] = len_key
    # 
    #         else:
    #             next_use[i] = visited_keys[key_arr[i]]
    #             visited_keys[key_arr[i]] = i
    
            next_use[i] = visited_keys.get(key_arr[i] , len_key)
            visited_keys[key_arr[i]] = i
    
        return next_use

    def get(self , key : int) -> bool:

        self.curr = self.position_counter
        self.position_counter += 1

        if key not in self.cache_dict:
            return False 

        else:
            self.cache_dict[key] = self.next_use_arr[self.curr]
            heapq.heappush(self.heap , HeapStore(next_use = -self.next_use_arr[self.curr] , key = key))
            return True 

    def put(self , key : int) -> None:

        if key in self.cache_dict:
            return

        if(len(self.cache_dict) >= self.capacity):

            while(True):
                
                popped_item = heapq.heappop(self.heap)
                
                if popped_item.key  in self.cache_dict and self.cache_dict[popped_item.key] == -popped_item.next_use :
                    del self.cache_dict[popped_item.key]
                    break

        self.cache_dict[key] = self.next_use_arr[self.curr]
        heapq.heappush(self.heap , HeapStore(next_use= -self.next_use_arr[self.curr] , key = key))
        
                

        

    
    
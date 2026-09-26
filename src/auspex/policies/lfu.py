from collections import OrderedDict

from auspex.policies.base import Policy


class LFU(Policy):

    name = "lfu"

    ''' 
    our lfu will have two structures in it for it to work. the first structure is a hash map which is mapped from 
    
    structure 1 : (url -> count / num of its occurance )
    
    this strucure shows which url has been used how many times hence satisfying the least frequently used format of LFU cache
    now we also have to evict the urls that have been least used and in case of a tie in count we have to decide somehow 
    whihc url we need to evict for this we will make our second strucuture 

    strucutre 2 : hashmap : count -> OrderedDict of urls

    now we make another hashmap which has mapping from count to the ordered dict of the urls now why are we using count as key ? 
    we are doing it for our eviction step we can maintain a min count and then chekc which urls have these counts 
    now why are we using ordered dict of urls as value , we are doing this cuz say we have multiple urls which has same count 
    so how do we decide which url we have to evict, for this we are using ordered dict , in whihc the most recently used urls 
    are kept at back and the least recently used urls are kept at first hence providing us with an easy way of eviction

    when we have to perform get() on a url we have to chnage its count and from that we can change its posiiton in structure 2
    for that we have to maintain structure 1.
    
    '''

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


        
            
    
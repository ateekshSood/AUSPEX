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
        self.url_count_map_structure = {}  #strucutre 1
        self.count_map_url_ordered_list = {} #structure 2
        self.min_count = -1 # min count frquency for eviction 

    def add_to_ordered_dict(self , key : int , new_count : int) -> None:

        # if the new count has no mapping 

        if new_count not in self.count_map_url_ordered_list:
            # make the new count's mapping
            self.count_map_url_ordered_list[new_count] = OrderedDict()

        # if it already has a mapping then simply add the url in the new count's ordered dict mapped to None.
        self.count_map_url_ordered_list[new_count][key] = None


    def key_in_map_handle(self , key : int) -> None:

        # we will have to update its count since we are interacting with it 

        #get old count from strucure 1
        old_count = self.url_count_map_structure[key]
        # get old ordered list for the old count from structure 2
        ordered_list_of_old_count = self.count_map_url_ordered_list[old_count]

        # delete the url from the ordered list of old count
        del ordered_list_of_old_count[key]

        # if the ordered list of old count has no elements left after evicitng the url 
        # then simply delete it 
        if not ordered_list_of_old_count :
            #delete the count mapping 
            del self.count_map_url_ordered_list[old_count]

            # if the count was min count then we will increment min count by 1 cuz the url's count has also increased by 1 
            # so we simply have to increase the min count by 1 cuz the old min count url is in an incremented by 1 count mapping
            if old_count == self.min_count:
                self.min_count +=1 

        #increase count
        self.url_count_map_structure[key] +=1

        #get new count
        new_count = self.url_count_map_structure[key]

        # helper fn to add in ordered dict
        self.add_to_ordered_dict(key , new_count) 
        
    # the fn to get the key from the cache

    def get(self , key : int) -> bool:

        #if it has a valid count in structure 1
        if key in self.url_count_map_structure:

            #helper fn for when key is found in the strucutre
            self.key_in_map_handle(key)
            
            return True 

        else:
            #key not found in the strucure
            return False 


    # fn to put a new key in the cache
    def put(self , key : int) -> None:

        # if the key is already in the strucutre 1 
        if key in self.url_count_map_structure:

            # we have decided that if the key is already in the cache we are not incrementng its 
            # frequency
            pass 
            
            
        # if the capacity of the strucutre is full
        elif len(self.url_count_map_structure) >= self.capacity:

            # pop the min count and the least recently used url and get the url 
            # it returns key that is url and value taht is None
            url_remove , _ = self.count_map_url_ordered_list[self.min_count].popitem(last = False)
            
            # delelte the url from structure 1
            del self.url_count_map_structure[url_remove]
            
            # if the ordered list of the min count is empty after eviction 
            if not self.count_map_url_ordered_list[self.min_count]:
                # delete the count mapping
                del self.count_map_url_ordered_list[self.min_count] 

            # for the new url make the mapping from new url -> 1 count
            self.url_count_map_structure[key] = 1 
            # since a new url has been inserted the min count will become 1
            self.min_count = 1

            # helper fn to add to ordered dict , the url in structure 2
            self.add_to_ordered_dict(key , self.min_count)

         
        else:

            # if the cache is not empty 

            # for the new url make the mapping from new url -> 1 count
            # since a new url has been inserted the min count will become 1
            
            self.url_count_map_structure[key] = 1
            self.min_count = 1

            # helper fn to add to ordered dict , the url in structure 2
            self.add_to_ordered_dict(key , self.min_count)


        
            
    
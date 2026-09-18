class Policy:

    def __init__(self , capacity : int):
        self.capacity = capacity
        
    
    def get(self , key : int) -> bool:
        """ True = hit . must also update frequency state on hit""" 
        raise NotImplementedError 

    def put(self , key : int) -> None:
        """ puts the key in the cache """
        raise NotImplementedError

    def observe(self , ts , session_id , key):
        pass 

    def on_tick(self ,ts):
        pass 

    def stats(self) -> dict:
        return {}
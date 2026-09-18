class Policy:

    name : str = "base"

    def __init__(self , capacity : int):
        self.capacity = capacity
        
    
    def get(self , key : int) -> bool:
        """ True = hit . must also update frequency/recency state on hit""" 
        raise NotImplementedError 

    def put(self , key : int) -> None:
        """ puts the key in the cache """
        raise NotImplementedError

    def observe(self , ts : int , session_id : int, key: int) -> None:
        """ our markov based learner will use this to observe the data check hit or miss and aim to learn 
            the patterns like user chooses request B after request A everytime so it will try to cache it 
            which would be a hit which would have been a miss otherwise
        """

    def on_tick(self ,ts: int) -> None:
        pass 

    def stats(self) -> dict:
        return {}
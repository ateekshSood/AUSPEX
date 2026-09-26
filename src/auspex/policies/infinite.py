from auspex.policies.base import Policy


class Infinite(Policy):

    name = "infinite"

    def __init__(self , capacity : int):
        super().__init__(capacity)
        self.url_set = set()

    def get(self , key : int) -> bool:

        return key in self.url_set 

    def put(self , key : int) -> None:

        self.url_set.add(key)
            
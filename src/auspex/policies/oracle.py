from xmlrpc.client import Boolean
import numpy as np

from auspex.policies.base import Policy


class Oracle(Policy):

    name = "oracle"

    def __init__(self , capacity : int , trace_url : np.ndarray , session_url : np.ndarray):
        self.capacity = capacity
        self.trace_url = trace_url
        self.session_url = session_url 
        self.next_session = np.zeros(len(self.trace_url) , dtype=np.int32)
        self.curr = 0
        self.backward_pass() 



    def backward_pass(self) -> None:

        url_dict = {}               
        
        for i in range(len(self.trace_url) -1 , -1 , -1):

            session = self.session_url[i]
            url = self.trace_url[i]

            if(session not in url_dict):
                self.next_session[i] = -1
                url_dict[session] = url 

            else:
                self.next_session[i] = url_dict[session]
                url_dict[session] = url
        
    def get(self , key : int) -> bool:
        
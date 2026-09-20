import numpy as np
import pandas as pd

from auspex.config import Cfg


def counted_mask(trace : pd.DataFrame , protocol : str , cfg : Cfg ) -> np.ndarray:

    #its just telling that we dont have to count the first warmup number enteries since they are for warming up the cache 
    if protocol.casefold() == "P1".casefold():
    
        counted_mask = np.zeros(len(trace) , dtype=bool)

        # THATS HOW NOOB WRITES AM NOOB YEAH
    
        # for index in range(len(counted_mask)):
    
        #     if index < int(len(trace) * cfg.warmup_frac):
        #         counted_mask[index] = False 
    
        #     else:
        #         counted_mask[index] = True 


        #THATS HOW PRO WRITES ... I DEF THOUGHT ABOUT IT MYSELF 

        warmup_n : int = int(len(trace) * cfg.warmup_frac) 
        counted_mask[warmup_n:] = True
    
        return counted_mask

    
    
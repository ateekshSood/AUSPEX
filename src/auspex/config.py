from dataclasses import dataclass

# python decorator dataclass as it will write the __init__ stuff on its own and i dont have to write it 
# without it i would have to write it 
# forzen = True is essentailly like public final in java
@dataclass(frozen=True)
class Cfg:
    # it means that gap more than 30 min 1800/60 in the session will end it  since in the data 
    # mulitple times we have like user perform action once then dont do anyting for like 2hrs 
    # then perform an action 
    # so this is for that it will essentailly make those two different actions 
    session_gap_s : int = 1800 

    #sessions longer than these number of requests will be flagged then dropoped since they are being done 
    # by bots (pls bots once you take over the world dont kill me)

    bot_max_session_len : int = 500 

    # just a fancy name it means we will divide the cachce into two parts the first is common using LRU and the second  
    # is our predictive cache and the ratio would be 20% of storage for the predictive model 
    # this is done to reduce cache pollution 
    prefetch_frac: float = 0.20


    #we need to fill the cache first to tell the performance 
    # this var simply tells how many requests will be used to fill it
    # say we are sending 100 requests then first 20 will be used to fil the cache 
    warmup_frac : float = 0.20

    # the max variation the session gap can have before they will be classified as bots 
    bot_cv_threshold : float = 0.1

    #how many min requests before bot will be flagged
    bot_cv_min_request : int = 100
    
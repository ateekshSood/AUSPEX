import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from auspex.config import Cfg
from auspex.harness.protocols import counted_mask
from auspex.harness.results import print_table, write_result
from auspex.policies.base import Policy
from auspex.policies.lru import LRU


def trace_loading(trace_name : str) -> dict:

    #the path for the parent will point to the parent auspex folder
    parent_path = Path(__file__).resolve().parents[3]

    #the path from the parent to the vocab parquet file
    vocab_trace_path = "data/processed/vocab.parquet"
    final_vocab_path = parent_path / vocab_trace_path 

    #path from the parent to the trace path 
    trace_path = "data/processed/NASA_access_log_cleaned_" + trace_name + ".parquet"
    final_trace_path = parent_path / trace_path

    # will load the trace parquet 
    trace_parquet = pd.read_parquet(final_trace_path)

    #check the order of the trace parquet 

    ts_check = np.diff(trace_parquet["ts"].to_numpy()) > 0
    seq_check = np.diff(trace_parquet["seq"].to_numpy()) > 0
    
    assert (ts_check | seq_check).all() , "The parquet is not sorted by (ts,seq) sort it..."
    
    # will load the vocab parquet which will have unique urls mapped to url id 
    vocab_parquet = pd.read_parquet(final_vocab_path)
    
    #modify the vocab trace inplace by setting the url as index
    vocab_parquet_indexed = vocab_parquet.set_index(vocab_parquet['url'])['url_id']
    
    # map the urls in the trace wiht the help of ids in the vocab of ids we built earlier
    ids = trace_parquet['url'].map(vocab_parquet_indexed)

    #check if any url has its id missing maybe some glitch 
    assert not ids.isna().any() , "map has empty elemetns error"

    #convert each pandas Series to numpy arrays then reuturn as dict for easy access
    ts_numpy , ids_numpy , session_id_numpy = trace_parquet['ts'].to_numpy() , ids.to_numpy() , trace_parquet['session_id'].to_numpy()

    return {"ts_numpy" : ts_numpy , "ids_numpy" : ids_numpy , "session_id_numpy" : session_id_numpy , "trace" : trace_parquet , "final_trace_path" : final_trace_path}

def policy_loop(policy : Policy  , len_trace : int , ts_numpy : np.ndarray , ids_numpy : np.ndarray , session_ids_numpy : np.ndarray  , counted_mask_output : np.ndarray) -> dict:

    hits , misses = 0 , 0
    start_time = time.perf_counter()
    
    for i in range(len_trace):
        policy.on_tick(ts_numpy[i])                 
        if policy.get(ids_numpy[i]):               
            if counted_mask_output[i]: hits += 1          
        else:
            if counted_mask_output[i]: misses += 1        
            policy.put(ids_numpy[i])               
        policy.observe(ts_numpy[i], session_ids_numpy[i], ids_numpy[i])

    end_time = time.perf_counter()

    return {"hits" : hits, "misses" : misses , "time_taken" : end_time - start_time}
    

def connector(trace_name : str):

    #get the output from the trace_loading the three numpy arrays 
    trace_loading_output = trace_loading(trace_name=trace_name)
    ts_numpy , ids_numpy , session_ids_numpy , trace_parquet , final_trace_path = trace_loading_output['ts_numpy'] ,trace_loading_output['ids_numpy'] , trace_loading_output['session_id_numpy'] , trace_loading_output['trace'] , trace_loading_output['final_trace_path']

    #call the output mask to get the cache warmup details
    cfg = Cfg()
    counted_mask_output = counted_mask(trace_parquet , "P1" , cfg )
    
    len_trace = len(trace_parquet)
    counted_ts = ts_numpy[counted_mask_output]
    
    table_print_list = []
    
    for size in [100 , 500 , 1000 , 5000 , 10000]:
        
        lru = LRU(size)
        policy_loop_output = policy_loop(lru , len_trace , ts_numpy , ids_numpy , session_ids_numpy  , counted_mask_output)

        hits , misses , wall_clock_s = policy_loop_output["hits"] , policy_loop_output["misses"] , policy_loop_output["time_taken"]
        
        _ = write_result(policy="lru" , capacity=size , protocol="P1" , trace_path=final_trace_path , cfg = cfg , hits = hits , misses= misses, 
            counted_requests=int(counted_mask_output.sum()) , wall_clock_s=wall_clock_s , counted_window=(counted_ts[0] , counted_ts[-1]) , policy_stats=lru.stats())

        temp = {"policy" : "lru" ,  "capacity" : size , "hit_rate" : hits/(hits + misses),
            "hits" : hits , "misses" : misses , "wall_clock_s" : wall_clock_s}

        table_print_list.append(temp)

    #function used to print the final resul table check the results.py for more detail 
    print_table(table_print_list)
        

def main():
    
    ap = argparse.ArgumentParser()
    ap.add_argument("-j" , action="store_true")
    ap.add_argument("-a" , action="store_true")
    args = ap.parse_args()

    #will print help if the user didnt give any arguments dont really need it ig cuz we have makefile and 
    # obv eveyrone gonna run that 
    if not args.j and not args.a:  
        ap.print_help()
        return 

    #if user gave -a as arg
    if args.a:

        connector("Aug95")

    #if they gave -j as arg
    if args.j:
        
        connector("Jul95")


if __name__ == "__main__":
    main()
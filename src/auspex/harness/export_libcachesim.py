import argparse
from pathlib import Path

import pandas as pd

from auspex.harness.replay import trace_loading


def save_csv(result : dict , trace_name : str):

    parent = Path(__file__).resolve().parents[3]
    location_name = "data/processed/" + trace_name + ".csv"
    final_path = parent / location_name

    ts , ids = result["ts_numpy"] , result["ids_numpy"]

    csv_trace = pd.DataFrame({"time" : ts , "ids" : ids})
    csv_trace.to_csv(final_path , index=False)

def connector(trace_name : str):

    result = trace_loading(trace_name)
    save_csv(result , trace_name)
    


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
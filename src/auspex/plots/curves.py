import json
from pathlib import Path

from auspex.harness.replay import POLICY_ARR, SIZE_ARR


def load_results() -> list[dict]:

    parent = Path(__file__).resolve().parents[3] #auspex
    result_path = parent / "results"

    json_files = result_path.glob("*P1.json")
    result_json = []

    for file in json_files:

        with open(file) as f:
            json_dict = json.load(f)

        result_json.append(json_dict)

    return result_json


def select_batch(results , batch=None) -> list[dict]:

    filtered_results = []

    if batch is  None:
        max_batch = max(results , key = lambda result : result["generated_at"])
        max_batch_run = max_batch["run_id"].split("_")[0]
        

    for result in results:

        if batch is not None:
            if result["run_id"].startswith(batch):
            
                filtered_results.append(result) 

        else:

            if(result["run_id"].startswith(max_batch_run)):
                filtered_results.append(result)

    if len(filtered_results) == 0:
   
        raise ValueError(f"no results matched batch : {batch}")
      
        
        
    
    return filtered_results

def check_batch(result_arr : list[dict]) -> None:

    set_git_sha = set()
    set_policy_combination = set()
    policy_arr = [p.name for p in POLICY_ARR]
    
    for result in result_arr:
        
    #check if they belong to the same commit 
        set_git_sha.add(result["git_sha"])
        set_policy_combination.add((result["policy"] , result["capacity"]))


    if len(set_git_sha) >1:
        raise ValueError("The results dont belong to the same commit")

    if next(iter(set_git_sha)).endswith("-dirty"):
        raise ValueError("The results are committed when other files were uncommitted . it has dirty git sha. Make sure the results are committed in its own commit")

    for policy_combination in set_policy_combination:

        
        if policy_combination[0] not in policy_arr:
            raise ValueError("The result array does not contain valid cache policy")

        if policy_combination[1] not in SIZE_ARR:
            raise ValueError("The result array's cache capacity size is not valid")

    if len(set_policy_combination) != len(result_arr):
        raise ValueError("The result array does not contain unique capacity and cache policies")

    if len(result_arr) != 20:
        raise ValueError("The lenght of result array is not equal to the unique policy and capacities combiantions")

def group_by_policy(batch) -> dict[str , list[tuple[int , float]]]:
    pass
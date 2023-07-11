# generation of random jobshop / flowshop benchmarks inspired by http://mistic.heig-vd.ch/taillard/articles.dir/Taillard1993EJOR.pdf

import sys
import random
import json


def generate_unsat_instance(jobs, machines, horizon, seed=0, flow=False):
  """Allows for a reduced maximum time with respect to the
  horizon and the number of jobs.
  """
  random.seed(seed)
  maxtime = max(horizon//jobs, 1)

  duration=[[0] * machines for _ in range(0,jobs)]
  for i in range(0,jobs):
    for j in range(0,machines):
      duration[i][j] = random.randint(1,maxtime)
  # #print("duration",duration)

  order = [list(range(0,machines)) for i in range(0,jobs)]
  if not flow:
    for i in range(0,jobs):
      random.shuffle(order[i])
  # #print("order",order)

  precedence = [[(i,j) for j in order[i]] for i in range(0,jobs)]
  # #print("precedence",precedence)

  return {
    "n_jobs": jobs,
    "task_to_mach": order,
    "duration": duration,
    "precedence": precedence,
    "horizon": horizon,
    "name": ("flowshop" if flow else "jobshop")+"_"+str(jobs)+"_"+str(machines)+"_"+str(horizon)+"_"+str(seed),
  }


def generate_instance(jobs, machines, horizon, seed=0, flow=False):
  random.seed(seed)
  maxtime = horizon// (jobs+1)


  duration=[[0] * machines for i in range(0,jobs)]
  for i in range(0,jobs):
    for j in range(0,machines):
      duration[i][j] = random.randint(1,maxtime)
  # #print("duration",duration)

  order = [list(range(0,machines)) for i in range(0,jobs)]
  if not flow:
    for i in range(0,jobs):
      random.shuffle(order[i])
  # #print("order",order)

  precedence = [[(i,j) for j in order[i]] for i in range(0,jobs)]
  # #print("precedence",precedence)

  return {
    "n_jobs": jobs,
    "task_to_mach": order,
    "duration": duration,
    "precedence": precedence,
    "horizon": horizon,
    "name": ("flowshop" if flow else "jobshop")+"_"+str(jobs)+"_"+str(machines)+"_"+str(horizon)+"_"+str(seed),
  }


if __name__ =="__main__":
    
  if len(sys.argv)!=6:
    #print("Usage: python3 jobshop.py #jobs:int #machines:int horizon:int seed:int flow:bool")
    #print("E.g.: python3 jobshop.py 5 4 10 0 False")
    exit(0)

  jobs = int(sys.argv[1])
  assert(jobs>0)
  machines = int(sys.argv[2])
  assert(machines>0)
  operations = jobs*machines
  horizon = int(sys.argv[3])
  assert(horizon>=jobs)
  seed = int(sys.argv[4])
  flow = sys.argv[5] in ["True","true","1", "yes"]
  #print("Generating job shop instance for",jobs,"jobs,",machines,"machines and",horizon,"time horizon, with seed",seed,"with flow precedence" if flow else "")

  data = generate_instance(jobs, machines, horizon, seed, flow)
  # #print(json.dumps(data))

  # #print("{")
  # for k,v in data.items():
  #   #print("  \"",k,"\":",sep="",end="");
  #   if isinstance(v,list):
  #     #print(" [\n",end="")
  #     for el in v:
  #       #print("    ",el,end=",\n")
  #     #print("  ],")
  #   else:
  #     #print(" ",v,",",sep="")
  # #print("}")

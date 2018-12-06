"""
'management' use case - the parent process is managing a pool of worker processes

python multiprocessing can achieve a similar goal only if the worker processes are
themselves python scripts. Here we can provide inputs to black-box executables that
accept inputs from stdin

worker accepts a list of tokens on separate lines, and outputs an aggregated result
"""
import ChildProcess

NUM_WORKERS = 10

cpb = ChildProcess.Builder(["worker", "-n", NUM_WORKERS, "-id", 0])

processes = []

for worker_id in range(NUM_WORKERS):
	cpb.args[4] = worker_id
	processes.append(cpb.spawn())

# some work to be divided up among the processes
tasks = ["foo", "bar", "baz", ...]

for (i, task) in enumerate(tasks):
	# select a worker in a cyclic manner
	process = processes[i % NUM_WORKERS]

	process.stdin.write("{}\n".format(task))

# add up results
total = 0
for process in processes:
	total += int(process.stdout.read_line().split()[0])

print("The result is {}".format(total))

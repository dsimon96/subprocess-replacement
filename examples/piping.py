"""
two piping examples using Doug McIlroy word-counting shell pipeline

The first example creates a ChildProcessBuilder for each command, piping them
together, and then spawns each of them individually.

The second example creates, pipes, and spawns all the processes at once with a
PipelineBuilder.

Note that in neither of these examples are shells actually spawned. The
ChildProcesses are piped together without having to rely on shell piping.
"""

from childprocess import ChildProcessBuilder as CPB
from childprocess import PipelineBuilder

words_to_count = b'one two three four five\n'

def run_manual_example():
    """
    First example - manual pipeline construction
    """
    print("Running first piping example - pipes manually assigned")

    tr1 = CPB("tr -cs A-Za-z '\n'")
    tr2 = CPB("tr A-Z a-z", stdin=tr1.stdout)
    sort1 = CPB("sort", stdin=tr2.stdout)
    uniq = CPB("uniq -c", stdin=sort1.stdout)
    sort2 = CPB("sort -rn", stdin=uniq.stdout)
    sed = CPB("sed ${1}q", stdin=sort2.stdout)

    procs = [tr1, tr2, sort1, uniq, sort2, sed]
    for proc in procs:
        proc.spawn()

    print("Piped {} processes together".format(len(procs)))
    print("Counting words in '{}'".format(words_to_count))
    print(dir(procs[0].stdin))
    procs[0].stdin.write(words_to_count)
    print("Counted {} words".format(procs[-1].readline()))

def run_auto_example():
    """
    Second example - automatic pipeline construction
    """
    print("Running second piping example - using Pipeline builder")

    procs = PipelineBuilder(["tr -cs A-Za-z '\n'",
                             "tr A-Z a-z",
                             "sort",
                             "uniq -c",
                             "sort -rn",
                             "sed ${1}q"]).spawn_all()

    print("Piped {} processes together".format(len(procs)))
    print("Counting words in '{}'".format(words_to_count))
    procs[0].stdin.write(words_to_count)
    print("Counted {} words".format(procs[-1].readline()))

if __name__ == "__main__":
    run_manual_example()
    run_auto_example()

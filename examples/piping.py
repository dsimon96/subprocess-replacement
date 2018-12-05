"""
'piping' use case

Doug McIlroy shell pipeline program
"""
from ChildProcess import Builder as CPB
from ChildProcess import Pipeline

tr1 = CPB("tr -cs A-Za-z '\n'")
tr2 = CPB("tr A-Z a-z", stdin=tr1.stdout)
sort1 = CPB("sort", stdin=tr2.stdout)
uniq = CPB("uniq -c", stdin=sort.stdout)
sort2 = CPB("sort -rn", stdin=uniq.stdout)
sed = CPB("sed ${1}q", stdin=sort2.stdout)

tr1.spawn()
tr2.spawn()
sort1.spawn()
uniq.spawn()
sort2.spawn()
sed.spawn()

Pipeline(["tr -cs A-Za-z '\n'",
   		  "tr A-Z a-z",
   		  "sort",
   		  "uniq -c",
   		  "sort -rn",
   		  "sed ${1}q"]).spawn()

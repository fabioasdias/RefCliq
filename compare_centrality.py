import json
import matplotlib.pylab as plt


with open('200.json') as fin:
    c10=json.load(fin)
with open('10.json') as fin:
    c100=json.load(fin)    

differences=[]
n10=0
n100=0
for n in c10['articles']:
    if ('centrality' in c10['articles'][n]) and ('centrality' in c100['articles'][n]):
        differences.append(abs(c10['articles'][n]['centrality']-c100['articles'][n]['centrality']))
        if (differences[-1]>0.4):
            print(c10['articles'][n])
            print('---')
            print(c100['articles'][n])
            input('.')
    else:
        if ('centrality' in c10['articles'][n]) and ('centrality' not in c100['articles'][n]):
            n100+=1
        if ('centrality' not in c10['articles'][n]) and ('centrality' in c100['articles'][n]):
            n10+=1

plt.figure()
plt.hist(differences)
plt.title('differences')
plt.figure()
plt.plot(sorted(differences))
plt.title('differences')

s10=[len(c10['partitions'][x]) for x in c10['partitions']]
s100=[len(c100['partitions'][x]) for x in c100['partitions']]
plt.figure()
plt.plot(s10,'x-',label='10')
plt.plot(s100,'x-',label='100')

print(n100,n10)
plt.show()
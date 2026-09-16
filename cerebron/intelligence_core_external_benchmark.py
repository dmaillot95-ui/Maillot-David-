from itertools import permutations
import random, json, statistics

# Objective benchmark: same tasks, same compute budget, same deterministic module implementations.
# This is NOT an AGI test. It tests whether module order changes externally scored task performance.

MODULES = ('C','M','I','V')

def make_tasks(seed=20260916, n=240):
    rng=random.Random(seed)
    tasks=[]
    # Family A: affine rules with one corrupted observation; infer and predict.
    for _ in range(n//4):
        a=rng.randint(-7,7) or 3; b=rng.randint(-20,20); xs=list(range(-3,5)); ys=[a*x+b for x in xs]
        j=rng.randrange(len(xs)); ys_bad=ys[:]; ys_bad[j]+=rng.choice([-9,-7,-5,5,7,9])
        q=rng.randint(6,15); tasks.append({'kind':'affine','xs':xs,'ys':ys_bad,'q':q,'ans':a*q+b})
    # Family B: quadratic integer rules with one corrupted observation.
    for _ in range(n//4):
        a=rng.randint(1,4); b=rng.randint(-5,5); c=rng.randint(-9,9); xs=list(range(-3,5)); ys=[a*x*x+b*x+c for x in xs]
        j=rng.randrange(len(xs)); ys_bad=ys[:]; ys_bad[j]+=rng.choice([-11,-7,7,11])
        q=rng.randint(6,12); tasks.append({'kind':'quad','xs':xs,'ys':ys_bad,'q':q,'ans':a*q*q+b*q+c})
    # Family C: arithmetic expressions with exactly one bad token; recover target.
    for _ in range(n//4):
        x=rng.randint(2,20); y=rng.randint(2,20); op=rng.choice(['+','-','*']); ans={'+':x+y,'-':x-y,'*':x*y}[op]
        bad=ans+rng.choice([-8,-4,4,8]); tasks.append({'kind':'check','x':x,'y':y,'op':op,'claim':bad,'ans':ans})
    # Family D: parity/modular classification under one mislabeled demonstration.
    for _ in range(n-len(tasks)):
        mod=rng.choice([3,4,5,7]); target=rng.randrange(mod); vals=list(range(1,17)); labels=[int(v%mod==target) for v in vals]
        j=rng.randrange(len(vals)); labels[j]=1-labels[j]; q=rng.randint(18,60); tasks.append({'kind':'mod','vals':vals,'labels':labels,'mod':mod,'q':q,'ans':int(q%mod==target)})
    rng.shuffle(tasks); return tasks

def hypotheses(task):
    # Generate a compact hypothesis set from observations.
    if task['kind']=='affine':
        hs=[]; xs,ys=task['xs'],task['ys']
        for i in range(len(xs)):
            for j in range(i+1,len(xs)):
                dx=xs[j]-xs[i]; dy=ys[j]-ys[i]
                if dx and dy%dx==0:
                    a=dy//dx; b=ys[i]-a*xs[i]
                    if -12<=a<=12: hs.append(('aff',a,b))
        return list(dict.fromkeys(hs))
    if task['kind']=='quad':
        hs=[]; xs,ys=task['xs'],task['ys']
        for i in range(len(xs)):
            for j in range(i+1,len(xs)):
                for k in range(j+1,len(xs)):
                    # solve 3x3 by brute small coefficients to keep equal budget/simple.
                    for a in range(1,5):
                        for b in range(-5,6):
                            c=ys[i]-a*xs[i]*xs[i]-b*xs[i]
                            if a*xs[j]*xs[j]+b*xs[j]+c==ys[j] and a*xs[k]*xs[k]+b*xs[k]+c==ys[k]: hs.append(('quad',a,b,c))
        return list(dict.fromkeys(hs))
    if task['kind']=='check': return [('claim',task['claim']),('calc',task['ans'])]
    if task['kind']=='mod': return [('mod',r) for r in range(task['mod'])]

def support(h,t):
    if h[0]=='aff': return sum(h[1]*x+h[2]==y for x,y in zip(t['xs'],t['ys']))
    if h[0]=='quad': return sum(h[1]*x*x+h[2]*x+h[3]==y for x,y in zip(t['xs'],t['ys']))
    if h[0]=='claim': return 0
    if h[0]=='calc': return 1
    if h[0]=='mod': return sum(int(v%t['mod']==h[1])==lab for v,lab in zip(t['vals'],t['labels']))

def predict(h,t):
    if h[0]=='aff': return h[1]*t['q']+h[2]
    if h[0]=='quad': return h[1]*t['q']*t['q']+h[2]*t['q']+h[3]
    if h[0]=='claim': return h[1]
    if h[0]=='calc': return h[1]
    if h[0]=='mod': return int(t['q']%t['mod']==h[1])

def run_order(order,t):
    state={'hs':hypotheses(t),'selected':None,'pred':None,'flags':set()}
    # Each module gets one pass, identical implementation independent of position.
    for m in order:
        if m=='C':
            # contradiction detection: flag hypotheses with weakest support.
            if state['hs']:
                scores=[support(h,t) for h in state['hs']]; mx=max(scores)
                state['flags']={i for i,s in enumerate(scores) if s<mx}
        elif m=='M':
            # metacognition: select most supported non-flagged hypothesis; uncertainty via ties.
            cand=[(support(h,t),i,h) for i,h in enumerate(state['hs']) if i not in state['flags']]
            if cand:
                cand.sort(reverse=True,key=lambda z:z[0]); state['selected']=cand[0][2]
                state['uncertain']=len(cand)>1 and cand[1][0]==cand[0][0]
        elif m=='I':
            # self-improvement: if uncertain or no selection, choose empirical best across all hypotheses.
            if state.get('selected') is None or state.get('uncertain',False):
                if state['hs']:
                    state['selected']=max(state['hs'],key=lambda h:support(h,t))
        elif m=='V':
            # verification: only emits prediction if selected hypothesis is not contradicted by majority evidence.
            h=state.get('selected')
            if h is not None:
                s=support(h,t)
                threshold=1 if t['kind']=='check' else (len(t.get('xs',t.get('vals',[])))-1)
                if s>=threshold: state['pred']=predict(h,t)
                elif t['kind']=='check' and h[0]=='calc': state['pred']=predict(h,t)
    return state['pred']

def main():
    tasks=make_tasks(); rows=[]
    for order in permutations(MODULES):
        correct=0; abstain=0
        fam={}
        for t in tasks:
            p=run_order(order,t); ok=(p==t['ans']); correct+=ok; abstain+=p is None
            fam.setdefault(t['kind'],[0,0]); fam[t['kind']][0]+=ok; fam[t['kind']][1]+=1
        rows.append({'order':''.join(order),'accuracy':correct/len(tasks),'correct':correct,'abstain':abstain,'families':{k:v[0]/v[1] for k,v in fam.items()}})
    rows.sort(key=lambda r:(r['accuracy'],-r['abstain']),reverse=True)
    out={'task_count':len(tasks),'orders':24,'metric':'exact-answer accuracy','equal_compute':True,'winner':rows[0],'ranking':rows,'note':'Deterministic external task benchmark; not evidence of AGI or superintelligence.'}
    print(json.dumps(out,indent=2)); open('intelligence_core_external_benchmark.json','w').write(json.dumps(out,indent=2))

if __name__=='__main__': main()

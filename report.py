#!/usr/bin/env python3
"""Derive deterministic article tables from the raw finite experiment records."""
import argparse,csv,json
from collections import Counter
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    sums=Counter(); bymode={m:Counter() for m in ('remined','pinned')}; table=[]
    for n in range(1,8):
        counts=Counter()
        with (a.results/f'population-{n}.csv').open(newline='') as stream:
            for r in csv.DictReader(stream):
                m=r['mode'];c=bymode[m]
                counts['configurations']+=1;counts['subset_checks']+=int(r['subset_count'])
                c['configurations']+=1
                if r['full_valid']=='1':
                    counts['full_valid']+=1;c['full_valid']+=1
                    if r['repeat_inclusion_minimal']=='0':
                        c['repeat_not_inclusion_minimal']+=1
                        if m=='remined':counts['repeat_failures']+=1
                    if r['singlepass_one_minimal']=='0':
                        c['singlepass_not_one_minimal']+=1
                        if m=='remined':counts['singlepass_failures']+=1
                    if int(r['repeat_size'])>int(r['optimum_size']):c['repeat_larger_than_minimum']+=1
                elif r['optimum_size']!='':c['invalid_full_with_valid_subset']+=1
        table.append(dict(n=n,**counts));sums.update(counts)
    horn=json.loads((a.results/'horn.json').read_text())
    result={'population_totals':dict(sums),'by_mode':{m:dict(c) for m,c in bymode.items()},'by_size':table,'horn':horn}
    (a.out/'summary.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    lines=[r'\begin{tabular}{rrrrrr}',r'\toprule',r'$n$ & Configurations & Subset checks & Full valid & Repeat failures & Pass failures \\',r'\midrule']
    for r in table:
        vals=[r['n'],r['configurations'],r['subset_checks'],r['full_valid'],r.get('repeat_failures',0),r.get('singlepass_failures',0)]
        lines.append(' & '.join(f'{x:,}' for x in vals)+r' \\')
    vals=[sums[k] for k in ('configurations','subset_checks','full_valid','repeat_failures','singlepass_failures')]
    lines += [r'\midrule','Total & '+' & '.join(f'{x:,}' for x in vals)+r' \\',r'\bottomrule',r'\end{tabular}']
    (a.out/'population-table.tex').write_text('\n'.join(lines)+'\n')
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()

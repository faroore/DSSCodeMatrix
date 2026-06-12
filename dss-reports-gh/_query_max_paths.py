import csv
from collections import defaultdict

LEVEL_ORDER = {'CHA':2,'REG':3,'BCH':4,'AOF':5,'SBR':6,'CORP':8,'AFF':9,'AGT':10}

# For each channel, find a sample record at the deepest level (AGT)
# and show the full context (region, branch, etc.) as the path values
with open('data/Advisors_by_Channel.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    
    # Group records by channel+branch_cd to find paths that span multiple levels
    by_channel_branch = defaultdict(lambda: defaultdict(list))
    for row in reader:
        ch = row.get('channel_name','').strip()
        lv = row.get('level_value','').strip()
        bc = row.get('branch_cd','').strip()
        if ch in ['IAC','CAC','NAC','DC','HO'] and lv and bc != 'NULL':
            by_channel_branch[ch][bc].append(row)

# For each channel, find the branch that has the most distinct levels
for ch in ['IAC','CAC','NAC','DC','HO']:
    print(f"\n{'='*80}")
    print(f"  {ch} — Max Data Path Samples")
    print(f"{'='*80}")
    
    # Find branches with max level coverage
    best_branches = []
    for bc, rows in by_channel_branch[ch].items():
        levels_present = set(r.get('level_value','').strip() for r in rows)
        best_branches.append((bc, levels_present, rows))
    
    best_branches.sort(key=lambda x: len(x[1]), reverse=True)
    
    # Show top 3 most complete paths
    shown = 0
    for bc, levels_present, rows in best_branches[:3]:
        sorted_levels = sorted(levels_present, key=lambda x: LEVEL_ORDER.get(x, 99))
        sorted_levels_no_agt = [l for l in sorted_levels if l != 'AGT']
        
        print(f"\n  Branch Code: {bc}")
        print(f"  Levels present: {len(sorted_levels)} → {' → '.join(sorted_levels)}")
        print(f"  Without AGT:    {len(sorted_levels_no_agt)} → {' → '.join(sorted_levels_no_agt)}")
        
        # Show one sample per level in this branch
        seen_levels = set()
        for lv in sorted_levels:
            for r in rows:
                if r.get('level_value','').strip() == lv and lv not in seen_levels:
                    seen_levels.add(lv)
                    fn = r.get('first_nm','').strip()
                    ln = r.get('last_nm','').strip()
                    name = f"{fn} {ln}".strip() if fn != 'NULL' else ln
                    ct = r.get('contract_type_nm','').strip()
                    cc = r.get('contract_cd','').strip()
                    rn = r.get('region_name','').strip()
                    bn = r.get('branch_name','').strip()
                    if bn == 'NULL':
                        bn = r.get('branch_name_hist','').strip()
                    rc = r.get('region_cd','').strip()
                    print(f"    L{LEVEL_ORDER.get(lv,'?'):>2} {lv:5s}: {name:<45s} Type: {ct:<8s} Code: {cc:<10s} Region: {rn}")
                    break
        shown += 1

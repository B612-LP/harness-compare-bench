#!/usr/bin/env python3
"""Pure algorithm experiment worker, never a product runner. Standard library only."""
import ast
from collections import deque
import hashlib
import json
from pathlib import Path
import sys
import types
import unittest

PAYLOAD_HASHES = {
    'before.py':'c139bc0b1b13b62b98986c9fdb79dd9f9ebe66564e9405d5cc3f3809da3c6168',
    'after.py':'c99b96b68ca54c4671d174d0801c80e2976b899550a3f1e8ce91ffca1b5395b6',
    'reference.py':'d1ca9185193402587a879e574a091b78d7a78e26b8b9a8d3696d780897e670fc',
    'canonical_test.py':'a5127ac17db6ad1563a08ba8ee2bbfc25ed8ab81ee56b92a355eb4a4dc2559fe',
}
# Each shape is independent input data, not obtained via a candidate path helper.
FIXTURES = {
    'singleton':['A',[]],
    'shallow':['A',[['B',[]],['C',[]],['D',[]]]],
    'chain3':['A',[['B',[['C',[]]]]]],
    'branched':['A',[['B',[['D',[['G',[]],['H',[]]]],['E',[]]]],['C',[['F',[]]]]]],
}

def require(ok,message):
    if not ok:raise ValueError(message)

def graph(shape):
    """Input/observed structure -> undirected adjacency, no candidate methods."""
    adjacency={}
    def visit(node,parent=None):
        require(type(node) is list and len(node)==2 and type(node[0]) is str and type(node[1]) is list,'shape')
        label,children=node
        require(label not in adjacency,'duplicate label/cycle')
        adjacency[label]=set()
        if parent is not None:
            adjacency[label].add(parent);adjacency[parent].add(label)
        for child in children:visit(child,label)
    visit(shape)
    return adjacency

def bfs(adjacency,start,end):
    """Independent shortest path, including both endpoints."""
    if start not in adjacency or end not in adjacency:return None
    queue=deque([[start]]);seen={start}
    while queue:
        path=queue.popleft()
        if path[-1]==end:return path
        for nxt in sorted(adjacency[path[-1]]):
            if nxt not in seen:seen.add(nxt);queue.append(path+[nxt])
    return None

def edges(adjacency):
    return sorted(sorted((a,b)) for a,neighbors in adjacency.items() for b in neighbors if a<b)

def make(Tree,shape):
    return Tree(shape[0],[make(Tree,c) for c in shape[1]])

def snapshot(tree):
    seen=set()
    def visit(node):
        require(id(node) not in seen,'node cycle/shared node')
        seen.add(id(node))
        require(type(node.label) is str and type(node.children) is list,'node shape')
        return [node.label,[visit(child) for child in node.children]]
    return visit(tree)

def read_payload(base,name):
    data=(base/name).read_bytes()
    require(hashlib.sha256(data).hexdigest()==PAYLOAD_HASHES[name],'payload identity mismatch: '+name)
    tree=ast.parse(data)
    # Additional review gate, not a hostile-code sandbox. Hash pin binds the reviewed bytes.
    allowed=('json','unittest','pov')
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):require(all(n.name in allowed for n in node.names),'import gate')
        if isinstance(node,ast.ImportFrom):require(node.module in allowed,'import-from gate')
    require(all(isinstance(n,(ast.Import,ast.ImportFrom,ast.ClassDef)) for n in tree.body),'top-level code gate')
    return data

def canonical(Tree,base):
    module=types.ModuleType('pov');module.Tree=Tree;sys.modules['pov']=module
    suite_module=types.ModuleType('canonical_suite')
    exec(compile(read_payload(base,'canonical_test.py'),'canonical_test.py','exec'),suite_module.__dict__)
    suite=unittest.defaultTestLoader.loadTestsFromModule(suite_module)
    discovered=suite.countTestCases();result=unittest.TestResult();suite.run(result)
    fail=sorted(t.id().split('.')[-1] for t,_ in result.failures)
    errors=sorted(t.id().split('.')[-1] for t,_ in result.errors)
    skipped=sorted(t.id().split('.')[-1] for t,_ in result.skipped)
    return {'discovered':discovered,'tests_run':result.testsRun,'failures':fail,'errors':errors,'skipped':skipped,'successes':result.testsRun-len(fail)-len(errors)-len(skipped)}

def oracle(Tree):
    reroot=[];paths=[];error_rows=[]
    for fid,shape in FIXTURES.items():
        original=graph(shape);labels=sorted(original);expected_edges=edges(original)
        for target in labels:
            source=make(Tree,shape);before=snapshot(source)
            try:
                out=source.from_pov(target);observed=snapshot(out);actual=graph(observed)
                immutable=snapshot(source)==before
                node_set=set(actual)==set(original);edge_set=edges(actual)==expected_edges
                connected=all(bfs(actual,observed[0],label) is not None for label in actual)
                pair_count=len(labels)**2
                matching=sum(bfs(actual,x,y)==bfs(original,x,y) for x in labels for y in labels)
                reroot.append({'fixture':fid,'target':target,'depth':len(bfs(original,shape[0],target))-1,'root_ok':observed[0]==target,'nodes_ok':node_set,'edges_ok':edge_set,'edge_count_ok':sum(map(len,actual.values()))//2==len(labels)-1,'connected':connected,'immutable':immutable,'all_pair_paths_checked':pair_count,'all_pair_paths_matching':matching,'expected_edges':expected_edges,'actual_edges':edges(actual),'exception':None})
            except Exception as exc:
                reroot.append({'fixture':fid,'target':target,'depth':len(bfs(original,shape[0],target))-1,'exception':type(exc).__name__})
        for start in labels:
            for end in labels:
                source=make(Tree,shape);before=snapshot(source);expected=bfs(original,start,end)
                try:
                    got=source.path_to(start,end)
                    paths.append({'fixture':fid,'from':start,'to':end,'expected':expected,'observed':got,'match':type(got) is list and got==expected,'immutable':snapshot(source)==before,'exception':None})
                except Exception as exc:
                    paths.append({'fixture':fid,'from':start,'to':end,'expected':expected,'observed':None,'match':False,'immutable':snapshot(source)==before,'exception':type(exc).__name__})
        for method,args,message in [('from_pov',['MISSING'],'Tree could not be reoriented'),('path_to',['MISSING',shape[0]],'Tree could not be reoriented'),('path_to',[shape[0],'MISSING'],'No path found')]:
            source=make(Tree,shape);before=snapshot(source)
            try:getattr(source,method)(*args);etype=None;msg=None
            except Exception as exc:etype=type(exc).__name__;msg=str(exc)
            error_rows.append({'fixture':fid,'method':method,'args':args,'exception':etype,'message':msg,'match':etype=='ValueError' and msg==message,'immutable':snapshot(source)==before})
    passed=lambda r:r.get('exception') is None and all(r[k] for k in ('root_ok','nodes_ok','edges_ok','edge_count_ok','connected','immutable')) and r['all_pair_paths_checked']==r['all_pair_paths_matching']
    return {'fixtures':FIXTURES,'reroot_rows':reroot,'path_rows':paths,'error_rows':error_rows,'summary':{'reroot_checked':len(reroot),'reroot_passed':sum(passed(r) for r in reroot),'path_checked':len(paths),'path_passed':sum(r['match'] and r['immutable'] for r in paths),'error_checked':len(error_rows),'error_passed':sum(r['match'] and r['immutable'] for r in error_rows),'original_immutable':all(r.get('immutable',False) for r in reroot+paths+error_rows)}}

def run(variant,base):
    require(variant in ('before','after','reference'),'variant')
    module=types.ModuleType('pov_candidate')
    exec(compile(read_payload(base,variant+'.py'),variant+'.py','exec'),module.__dict__)
    return {'variant':variant,'canonical':canonical(module.Tree,base),'oracle':oracle(module.Tree)}

if __name__=='__main__':
    require(len(sys.argv)==2,'one variant required')
    result=run(sys.argv[1],Path(__file__).resolve().parent)
    print(json.dumps({'optimize':sys.flags.optimize,'result':result},ensure_ascii=False,sort_keys=True))

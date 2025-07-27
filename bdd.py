import sys
from collections import namedtuple, defaultdict
from typing import Tuple, Dict


def readNetlist(file):
    nets = int(file.readline())
    inputs  = file.readline().split()
    inputs.sort()
    outputs = file.readline().split()
    outputs.sort()

    # read mapping
    mapping = {}
    while True:
        line = file.readline().strip()
        if not line:
            break

        net,name = line.split()
        mapping[name] = int(net)

    # read gates
    gates = []
    for line in file.readlines():
        bits = line.split()
        gate = bits.pop(0)
        ports = map(int,bits)
    
        gates.append((gate,ports))
        
    return inputs,outputs,mapping,gates

# read netlists
inputs1,outputs1,mapping1,gates1 = readNetlist(open(sys.argv[1],"r"))
inputs2,outputs2,mapping2,gates2 = readNetlist(open(sys.argv[2],"r"))

# add your code here!
# Define a BDD Node as a namedtuple
class BDDNode:
    def __init__(self, var, low, high):
        self.var = var
        self.low = low
        self.high = high

    def __eq__(self, other):
        return (self.var, self.low, self.high) == (other.var, other.low, other.high)

    def __hash__(self):
        return id(self)
    
    def replace_net(self, net, input):
        if self.var == -1 or self.var == -2:
            return
        if self.var == net:
            self.var = input
        self.low.replace_net(net, input)
        self.high.replace_net(net, input)

# Terminal nodes
BDD_TRUE = BDDNode(-1, None, None)
BDD_FALSE = BDDNode(-2, None, None)

def make_bdd(var, low, high):
    if low == high:
        return low  # Eliminate redundant node
    node = BDDNode(var, low, high)
    return node

# ITE cache
ite_cache: list[Dict[int, BDDNode]] = []
ite_cache.append({0: BDD_TRUE})
ite_cache.append({0: BDD_TRUE})


def cofactor(f:BDDNode, x):
    if f == BDD_TRUE or f == BDD_FALSE or f.var > x:
        return (f, f)
    if f.var == x:
        return (f.low, f.high)
    lo0, lo1 = cofactor(f.low, x)
    hi0, hi1 = cofactor(f.high, x)
    return (make_bdd(f.var, lo0, hi0), make_bdd(f.var, lo1, hi1))



def ite(f:BDDNode, g:BDDNode, h:BDDNode):
    if f == BDD_TRUE:
        return g
    if f == BDD_FALSE:
        return h
    if g == h:
        return g
    if g == BDD_TRUE and h == BDD_FALSE:
        return f

    top = max([f.var,g.var,h.var])

    f0, f1 = cofactor(f, top)
    g0, g1 = cofactor(g, top)
    h0, h1 = cofactor(h, top)

    l = ite(f0, g0, h0)
    r = ite(f1, g1, h1)

    result = make_bdd(top, l, r)
    return result

# Gate functions via ITE
def apply_gate(gate_type, a, b=None):
    if gate_type == "and":
        return ite(a, b, BDD_FALSE)
    elif gate_type == "or":
        return ite(a, BDD_TRUE, b)
    elif gate_type == "inv":
        return ite(a, BDD_FALSE, BDD_TRUE)
    elif gate_type == "xor":
        return ite(a, ite(b, BDD_FALSE, BDD_TRUE), b)
    else:
        raise ValueError(f"Unknown gate type: {gate_type}")


def build_bdd(inputs, ouputs, mapping, gates, circuit:int):
    for i in inputs:
        #dict (input netlist) --> (BDD)
        net = mapping[i]
        ite_cache[circuit][net] = make_bdd(net, BDD_FALSE, BDD_TRUE)

    for gate in gates:
        if(gate[0] == "inv"):
            ite_cache[circuit][gate[2]] = apply_gate(gate[0], ite_cache[circuit][gate[1]])
        else:
            ite_cache[circuit][gate[3]] = apply_gate(gate[0], ite_cache[circuit][gate[1]], ite_cache[circuit][gate[2]])

def are_equivalent(out1, map1, map2):
    for o in out1:
        net1 = map1[o]
        net2 = map2[o]
        if(ite_cache[0][net1] != ite_cache[1][net2]):
            return False
    return True

def replace_inputnets_with_inputnames():
    for output in outputs1:
        out_net = mapping1[output]
        for input in inputs1:
            in_net = mapping1[input]
            ite_cache[0][out_net].replace_net(in_net, input)
    for output in outputs2:
        out_net = mapping2[output]
        for input in inputs2:
            in_net = mapping2[input]
            ite_cache[1][out_net].replace_net(in_net, input)

def addthousand(x):
    return x+1000

#remove map type from gates1,gates2
for idx,gate in enumerate(gates1):
    ports = list(gate[1])
    if gate[0] == "inv":
        gates1[idx] = [gate[0], ports[0], ports[1]]
    else:
        gates1[idx] = [gate[0], ports[0], ports[1], ports[2]]
for idx,gate in enumerate(gates2):
    ports = list(gate[1])
    if gate[0] == "inv":
        gates2[idx] = [gate[0], ports[0], ports[1]]
    else:
        gates2[idx] = [gate[0], ports[0], ports[1], ports[2]]
    

#rename nets in gates2 based on input nets in mappings1
for key,value in mapping2.items():#add 1000 to nets in mapping2
    mapping2[key] = value+1000
for idx,gate in enumerate(gates2):#add 1000 to nets in gates2
    if gate[0] == "inv":
        gates2[idx] = [gate[0], gate[1]+1000, gate[2]+1000]
    else:
        gates2[idx] = [gate[0], gate[1]+1000, gate[2]+1000, gate[3]+1000]
for key1,value1 in mapping1.items():
    for key2,value2 in mapping2.items():
        if key2 == key1:
            mapping2[key2] = value1
            for idx,gate in enumerate(gates2):
                if gate[1] == value2: gate[1] = value1
                if gate[2] == value2: gate[2] = value1
                if gate[0] != "inv":
                    if gate[3] == value2: gate[3] = value1 
                gates2[idx] = gate



build_bdd(inputs1, outputs1, mapping1, gates1, 0)
build_bdd(inputs2, outputs2, mapping2, gates2, 1)
replace_inputnets_with_inputnames()#just for debugging purpose

print("are equivalent? " + str(are_equivalent(outputs1, mapping1, mapping2)))
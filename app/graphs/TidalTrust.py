import sys
import networkx as nx
from copy import deepcopy
from itertools import chain
import matplotlib.pyplot as plt

#reference: https://github.com/mvk-team42/Veracitor

def tidal_trust(source, sink, graph, tag):
    results = {"trust": None,
               "threshold": None,
               "paths_used": [],
               "nodes_used": [],
               "nodes_unused": [],
               "source": source,
               "sink": sink,
               "tag": tag,
               }
    '''
    remove_list = [(x,y) for (x,y) in graph.edges() if tag not in graph[x][y]]
    graph.remove_edges_from(remove_list)
    '''
    shortest = nx.all_shortest_paths(graph,source = source, target = sink)
    paths_list = list(shortest)

    threshold = get_threshold(paths_list, graph, tag)
    results['threshold'] = threshold
    
    useful_paths = remove_low_rated_paths(paths_list, threshold, graph, tag)
    results["paths_used"] = useful_paths
    results["nodes_used"] = list(set(chain.from_iterable(useful_paths)))

    # Add unused nodes (not in shortest path) to results
    path_nodes = set(chain.from_iterable(useful_paths))
    results["nodes_unused"] += [n for n in graph.nodes() if n not in path_nodes]
    
    queue = []

    for i in reversed(range(len(useful_paths[0])-2)):
        for j in range(len(useful_paths)):
            if(useful_paths[j][i] not in queue):
                # Add to queue for backwards search
                queue.append(useful_paths[j][i])
    
    cached_trust = {}
    for n in range(len(useful_paths)):
        # Select predecessors of sink in path n
        sink_neighbor = useful_paths[n][len(useful_paths[0])-2]   
        if (sink_neighbor, sink) not in cached_trust:
            cached_trust[(sink_neighbor, sink)] = graph[sink_neighbor][sink][tag]

    while queue:
        current_node = queue.pop(0)    
        children = graph.successors(current_node) # Get all children of current_node
        numerator = float(0)
        denominator = float(0)
        for s in children:
            # Use edge if rating >= threshold and the successor has a cached trust to the sink.
            if (graph[current_node][s][tag] >= threshold and (s, sink) in cached_trust):
                if cached_trust[(s, sink)] >= 0:
                    numerator = (numerator + 
                                 graph[current_node][s][tag]*cached_trust[(s, sink)])
                    denominator = denominator + graph[current_node][s][tag]
        
        if denominator > 0:
            cached_trust[(current_node, sink)] = numerator / denominator                                
    
        # Sets trust to -1 if no children could be used (e.g., ratings below threshold)
        else:
            cached_trust[(current_node, sink)] = -1       
            results["nodes_unused"].append(current_node)
        
    
    if (source, sink) in cached_trust:
        results["trust"] = round(cached_trust[(source, sink)],1)
        if threshold == sys.maxsize:
            results["threshold"] = results["trust"]

    return results

def get_threshold(paths, graph, tag):
    """
    Calculates the threshold used to exclude paths in the TidalTrust algorihm. 
    Returns the maximum trust of the lowest trust in each individual path
    """
    threshold = 0
    min_path_weight = 0
    for path in paths:
        
        for i in range(len(path)-2):
            
            min_path_weight = graph[path[i]][path[i+1]][tag]
        
        if min_path_weight > threshold:
            threshold = min_path_weight  

    return threshold

def remove_low_rated_paths(paths, threshold, graph, tag):
    """
    Removes paths from a list of paths that contains weights below the threshold.
    
    """
    relevant_paths = paths[:]
    for path in paths:
        for i in range(len(path)-2):
            if graph[path[i]][path[i+1]][tag] < threshold:
               relevant_paths.remove(path)
            continue
    
    return relevant_paths

def compute_trust(network, source, sink, decision=None, tag="weight"):
     #check input
    if network == None or source == None or sink == None:
        raise TypeError("Input parameters can't be None")

    network = deepcopy(network)

    # Ignore nodes as specified by decision
    if decision != None:
        network.remove_nodes_from(decision)
   
    trust_results = tidal_trust(graph=network, source=source, sink=sink, tag=tag)
    
    return trust_results
    

#test    
sample = [{'username': 'Alice',
                   'followers': [{'followers_username': 'Arthur',
                                  'followers_count': 2}]},
                  {'username': 'Arthur',
                   'followers': [{'followers_username': 'Alice', 'followers_count': 3},
                                 {'followers_username': 'Kate', 'followers_count': 4}]},
                  {'username': 'Kate',
                   'followers': [{'followers_username': 'Bill', 'followers_count': 245},
                                 {'followers_username': 'P3t3r', 'followers_count': 21},
                                 {'followers_username': 'Derek', 'followers_count': 2},
                                 {'followers_username': 'ZooMan123', 'followers_count': 21}]},
                  {'username': 'Derek',
                   'followers': [{'followers_username': 'Shane', 'followers_count': 12},
                                 {'followers_username': 'Carly', 'followers_count': 2},
                                 {'followers_username': 'Superman', 'followers_count': 32}]}]
i = 0
j = 0
G = nx.DiGraph()
edges = []
for i in range(len(sample)):
    for j in range(len(sample[i]['followers'])):
        edges.append((sample[i]['username'],sample[i]['followers'][j]['followers_username']))
        G.add_edge(sample[i]['username'],sample[i]['followers'][j]['followers_username'],dict(attr = 1))
result = tidal_trust('Alice','Derek', G,'attr')
pos=nx.spring_layout(G)

labels = {}
for node in G.nodes():
    labels[node] = node

nx.draw_networkx_nodes(G, pos, nodelist = result['nodes_used'], node_color = 'r')
nx.draw_networkx_nodes(G, pos, nodelist = result['nodes_unused'], node_color = 'b')
nx.draw_networkx_edges(G, pos, edgelist = edges)

nx.draw_networkx_labels(G, pos, labels)
plt.axis('off')
#plt.savefig('tidal trust path.png')
plt.show()

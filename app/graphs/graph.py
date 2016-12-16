import networkx as nx
import matplotlib.pyplot as plt

egoUser = 'U'
followers = ['A', 'B', 'C', 'D', 'E', 'F']
followees = ['C', 'D', 'F', 'G', 'H']

DG = nx.DiGraph()
e_followers = [(egoUser, f) for f in followers]

filtered_followees = [t for t in followees if t in followers]
e_followees = [(t, egoUser) for t in filtered_followees]

DG.add_edges_from(e_followers, color = 'blue')
DG.add_edges_from(e_followees, color = 'red')

labels = {}
for node in DG.nodes():
    labels[node] = node

pos=nx.spring_layout(DG)

nx.draw_networkx_nodes(DG, pos, nodelist = followers, node_color = 'b')
nx.draw_networkx_nodes(DG, pos, nodelist = [egoUser], node_color = 'r')

nx.draw_networkx_edges(DG, pos, edgelist = e_followers, edge_color = 'b', arrows = True)
nx.draw_networkx_edges(DG, pos, edgelist = e_followees, edge_color = 'r', arrows = True)

nx.draw_networkx_labels(DG, pos, labels)
plt.axis('off')
#plt.savefig('relationship_map.png')
plt.show()


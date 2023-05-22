import networkx as nx


def eval_centrality(g, edge_centrality_fn, node_centrality_fn, weight, inplace=True):
    if not inplace:
        g = g.copy()
    nodes_centrality = node_centrality_fn(g, weight=weight)
    edges_centrality = edge_centrality_fn(g, weight=weight)

    for (u, v, i), centrality in edges_centrality.items():
        g[u][v][i]['centrality'] = centrality

    for node, centrality in nodes_centrality.items():
        g.nodes[node]['centrality'] = centrality

    return g


def eval_difference(g1, g2):
    g = g1.copy()
    # clean g attrs
    for _, _, a in g.edges(data=True):
        if 'centrality' in a:
            a['centrality'] = -1
    for _, a in g.nodes(data=True):
        if 'centrality' in a:
            a['centrality'] = -1

    # eval diff for edges
    for u, v in g.edges():
        if g1.has_edge(u, v) and g2.has_edge(u, v) and \
           'centrality' in g1[u][v][0] and 'centrality' in g2[u][v][0]:
            g[u][v][0]['centrality'] = g1[u][v][0]['centrality'] - g2[u][v][0]['centrality']
    # eval diff for nodes
    for u in g.nodes():
        if g1.has_node(u) and g2.has_node(u) and \
           'centrality' in g1.nodes[u] and 'centrality' in g2.nodes[u]:
            g.nodes[u]['centrality'] = g1.nodes[u]['centrality'] - g2.nodes[u]['centrality']

    # drop missing edges between graphs
    edges_to_remove = []
    for u, v, a in g.edges(data=True):
        if a['centrality'] < 0:
            edges_to_remove.append((u, v))
    for u, v in edges_to_remove:
        g.remove_edge(u, v)

    return g
import networkx as nx


def get_most_popular_roads(G: nx.MultiDiGraph, n):
    return [x[2] for x in sorted(G.edges(data=True), key=lambda x: -1 * x[2]['centrality'])[:n]]

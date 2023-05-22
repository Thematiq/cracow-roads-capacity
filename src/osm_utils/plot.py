import osmnx as ox


def plot_centrality(g):
    return ox.plot_graph(g, node_color=ox.plot.get_node_colors_by_attr(g, attr='centrality'),
              edge_color=ox.plot.get_edge_colors_by_attr(g, attr='centrality', cmap='plasma'),
              figsize=(16, 9))

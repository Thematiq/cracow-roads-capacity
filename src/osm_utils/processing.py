import networkx as nx
import osmnx as ox


def engineer_features(G: nx.MultiGraph) -> nx.MultiGraph:
    for u, v, a in G.edges(data=True):
        if 'maxspeed' not in a:
            a['maxspeed'] = 50
        if isinstance(a['maxspeed'], list):
            a['maxspeed'] = min(a['maxspeed'])
        elif isinstance(a['maxspeed'], dict):
            print(a)

        if isinstance(a['maxspeed'], str):
            a['maxspeed'] = float(a['maxspeed'])

        a['travel_time'] = a['length'] / a['maxspeed']

        G[u][v][0]['travel_time'] = a['travel_time']
    return G


def find_roads(g, road_name):
    names = set()
    for u, v, a in g.edges(data=True):
        if 'name' in a and road_name in a['name']:
            names.add(a['name'])
    return names


def delete_road(g, road_name, inplace=False):
    if not inplace:
        g = g.copy()

    edges_to_remove = []
    for u, v, a in g.edges(data=True):
        if ('name' in a and road_name == a['name']) or ('ref' in a and road_name == a['ref']):
            edges_to_remove.append((u, v))
    for u, v in edges_to_remove:
        g.remove_edge(u, v)
    print(f'Deleted {len(edges_to_remove)} edges')
    return g


def read_graph(city: str, tolerance: float, buffer: float = None):
    G = ox.graph_from_place(city,
                            network_type='drive',
                            buffer_dist=buffer)
    G = ox.project_graph(G)
    G = ox.consolidate_intersections(G, tolerance=tolerance)
    return engineer_features(G)

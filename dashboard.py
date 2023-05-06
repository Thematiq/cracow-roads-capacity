import folium

import matplotlib as mpl
import streamlit as st
import osmnx as ox
import networkx as nx

from matplotlib import cm
from dataclasses import dataclass
from streamlit_folium import folium_static
from joblib import Memory

cache_dir = '.cache/'

CACHE = Memory(location=cache_dir)

st.set_page_config(
    layout='wide'
)

centrality_mapping = {
    'betweenness': (
        nx.betweenness_centrality,
        nx.edge_betweenness_centrality
    ),
    'random walk betweenness': {
        nx.current_flow_betweenness_centrality,
        nx.edge_current_flow_betweenness_centrality
    }
}


@dataclass
class InputData:
    city_name: str
    intersection_tolerance: float


def find_roads(g, road_name):
    names = set()
    for u, v, a in g.edges(data=True):
        if 'name' in a and road_name in a['name']:
            names.add(a['name'])
    return names


def all_roads(g):
    names = set()
    for u, v, a in g.edges(data=True):
        if 'name' in a and not isinstance(a['name'], list):
            names.add(a['name'])
    return names


def delete_road(g, road_name, inplace=False):
    if not inplace:
        g = g.copy()

    edges_to_remove = []
    for u, v, a in g.edges(data=True):
        if 'name' in a and road_name == a['name']:
            edges_to_remove.append((u, v))
    for u, v in edges_to_remove:
        g.remove_edge(u, v)
    print(f'Deleted {len(edges_to_remove)} edges')
    return g


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


@st.cache_resource
def read_graph(city_name: str, tolerance: float) -> nx.MultiGraph:
    G = ox.graph_from_place(city_name, network_type='drive', simplify=True)
    G = ox.project_graph(G)
    G2 = ox.consolidate_intersections(G, tolerance=tolerance)
    return engineer_features(G2)


def input_panel() -> InputData:
    return InputData(
        city_name=st.text_input(label='Area name'),
        intersection_tolerance=st.slider('Intersection consolidation tolerance (in meters)',
                                         min_value=1, max_value=100)
    )


def get_min_max_prop(_streets, attr):
    p = _streets[attr]
    return p.min(), p.max()


def get_cmap(vmin, vmax, cmap='viridis'):
    cmap = cm.get_cmap(cmap)
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
    final_cmap = cm.ScalarMappable(norm=norm, cmap=cmap)
    return final_cmap


def edge_embedding(hex_val):
    return {'color': hex_val, 'weight': '3'}


def node_embedding(hex_val):
    return {'color': hex_val}


def style_fun(properties, embed, attr='maxspeed', vmin=0, vmax=100, *_args):
    properties = properties['properties']
    final_cmap = get_cmap(vmin, vmax)

    if attr in properties and properties[attr] is not None:
        if isinstance(properties[attr], list):
            speed = min(map(float, properties[attr]))
        else:
            speed = float(properties[attr])
        rgba = final_cmap.to_rgba(speed)
        hex_val = mpl.colors.rgb2hex(rgba)
    else:
        hex_val = '#000000'

    return embed(hex_val)


@CACHE.cache()
def edges_geojson(_streets, attr, city_name):
    vmin, vmax = get_min_max_prop(_streets, attr)
    return folium.GeoJson(_streets,
                          style_function=lambda *x: style_fun(embed=edge_embedding, vmin=vmin, vmax=vmax, attr=attr, *x))


@CACHE.cache()
def nodes_geojson(_nodes, attr, city_name):
    vmin, vmax = get_min_max_prop(_nodes, attr)
    return folium.GeoJson(_nodes,
                          marker=folium.CircleMarker(
                              radius=3,
                          ),
                          style_function=lambda *x: style_fun(embed=node_embedding, vmin=vmin, vmax=vmax, attr=attr, *x)
                          )


def generate_folium(G, city_name, edge_attr='maxspeed', node_attr=None):
    nodes, streets = ox.graph_to_gdfs(G)
    m = folium.Map(location=ox.geocode(city_name))
    edges_geojson(streets, edge_attr, city_name).add_to(m)
    if node_attr is not None:
        nodes_geojson(nodes, edge_attr, city_name).add_to(m)
    return m


@CACHE.cache(ignore=['edge_centrality_fn', 'node_centrality_fn', 'inplace'])
def eval_centrality(g, edge_centrality_fn, node_centrality_fn, weight, _city_name, _centrality, inplace=False):
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


@CACHE.cache(ignore=['G'])
def perform_centrality_analysis(G, roads_to_remove, centrality, city_name):
    node_centrality, edge_centrality = centrality_mapping[centrality]

    with st.spinner('Evaluating original centrality'):
        og_centrality = eval_centrality(
            G,
            edge_centrality_fn=edge_centrality,
            node_centrality_fn=node_centrality,
            _city_name=city_name,
            _centrality=centrality,
            weight='travel_time'
        )

    with st.spinner('Evaluting post edit centrality'):
        G2 = G

        for road in roads_to_remove:
            G2 = delete_road(G, road)

        new_centrality = eval_centrality(
            G2,
            edge_centrality_fn=edge_centrality,
            node_centrality_fn=node_centrality,
            _city_name=city_name,
            _centrality=centrality,
            weight='travel_time'
        )

    col1, col2 = st.columns(2)

    with col1:
        """### Original centrality"""
        with st.spinner('Calculating graph embedding'):
            fol = generate_folium(og_centrality, city_name, edge_attr='centrality',
                                  node_attr='centrality')

        folium_static(fol, width=600, height=350)

    with col2:
        """### After removal centrality"""
        with st.spinner('Calculating graph embedding'):
            fol = generate_folium(new_centrality, city_name, edge_attr='centrality',
                                  node_attr='centrality')

        folium_static(fol, width=600, height=350)

    with st.spinner('Calculating difference'):
        centrality_diff = eval_difference(new_centrality, og_centrality)

    """### Centrality difference """
    with st.spinner('Calculating graph embedding'):
        fol = generate_folium(centrality_diff, city_name, edge_attr='centrality',
                              node_attr='centrality')

    folium_static(fol, width=1300, height=500)


def main():
    with st.sidebar:
        """## Visualization parameters"""
        data = input_panel()
        G = read_graph(data.city_name, data.intersection_tolerance)
        attr = st.selectbox(
            label='Plotted property',
            options=['maxspeed', 'travel_time']
        )
        centrality = st.selectbox(
            label='Centrality function',
            options=centrality_mapping.keys()
        )

    """# Graph"""
    with st.spinner('Calculating graph embedding'):
        fol = generate_folium(G, data.city_name, edge_attr=attr)

    # fol = cache_graph(**data.__dict__)
    folium_static(fol, width=1200, height=700)

    roads = st.multiselect('Roads to be removed', options=all_roads(G))

    if st.button('Run calculations'):
        perform_centrality_analysis(G, roads, centrality, data.city_name)


main()

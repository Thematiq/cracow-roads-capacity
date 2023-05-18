import folium

import streamlit as st
import osmnx as ox
import networkx as nx
import geopandas as gpd

from math import sqrt
from dataclasses import dataclass
from streamlit_folium import st_folium
from shapely.geometry import Point


@dataclass
class BasicInput:
    city_name: str
    file_name: str
    intersection_tolerance: float


def basic_input():
    return BasicInput(
        city_name=st.text_input(label='Area name'),
        file_name=st.text_input(label='Output file name'),
        intersection_tolerance=st.slider('Intersection consolidation'
                                         'tolerance (in meters)', min_value=1,
                                         max_value=100)
    )


@st.cache_resource
def read_city(data: BasicInput) -> nx.MultiDiGraph:
    G = ox.graph_from_place(data.city_name, network_type='drive',
                            simplify=True)
    G = ox.project_graph(G)
    G2 = ox.consolidate_intersections(G, tolerance=data.intersection_tolerance)
    return G2


@st.cache_resource
def generate_folium(_G, params):
    nodes, streets = ox.graph_to_gdfs(_G)
    m = folium.Map(location=ox.geocode(params.city_name))
    folium.GeoJson(streets).add_to(m)
    folium.GeoJson(nodes, marker=folium.CircleMarker(radius=3)).add_to(m)
    return m


def prepare_cache():
    if 'nodes_in_progress' not in st.session_state:
        st.session_state['nodes_in_progress'] = []
    if 'paths_to_add' not in st.session_state:
        st.session_state['paths_to_add'] = []
    if 'paths_to_remove' not in st.session_state:
        st.session_state['paths_to_remove'] = []


# def find_closest_node(G, lat, lon, epsilon=1e-5):
#     nodes = []
#     for u, a in G.nodes(data=True):
#         a_lat = a['y']
#         a_lon = a['x']
#         dist = abs(lat - a_lat) + abs(lon - a_lon)
#         # if dist < epsilon:
#         nodes.append((dist, u))
#     # if len(nodes) == 0:
#     #     return None
#     return min(nodes)



def find_closest_node(G, lat, lon, epsilon=1e-5):
    p = [Point(lon, lat)]
    p = gpd.GeoSeries(p, crs='epsg:4326')
    p = p.to_csr(G.graph['crs'])
    return [ox.get_nearest_node(G, (pt.y, pt.x), 'euclidean') for pt in p]


def main():
    prepare_cache()
    """# OSM parameters"""
    params = basic_input()
    G = read_city(params)
    fol = generate_folium(G, params)
    res = st_folium(fol)

    if res['last_clicked'] is not None:
        st.session_state['nodes_in_progress'].append(res['last_clicked'])
        closest = res['last_clicked']
        f"""Last node clicked: {closest}"""
        f"""Closest node: {find_closest_node(G, closest['lat'], closest['lng'])}"""


    print(res)


main()

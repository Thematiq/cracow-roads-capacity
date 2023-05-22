import folium

import matplotlib as mpl
import osmnx as ox

from matplotlib import cm


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


def edges_geojson(_streets, attr):
    vmin, vmax = get_min_max_prop(_streets, attr)
    return folium.GeoJson(_streets,
                          style_function=lambda *x: style_fun(embed=edge_embedding, vmin=vmin, vmax=vmax, attr=attr, *x))


def nodes_geojson(_nodes, attr):
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
    edges_geojson(streets, edge_attr).add_to(m)
    if node_attr is not None:
        nodes_geojson(nodes, edge_attr).add_to(m)
    return m

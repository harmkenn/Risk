import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from risk_game import RiskGame

# Example simple map for demo (6 territories, 2 continents)
TERRITORY_MAP = {
    "Alaska": ["Northwest Territory", "Alberta"],
    "Northwest Territory": ["Alaska", "Alberta", "Ontario"],
    "Alberta": ["Alaska", "Northwest Territory", "Ontario"],
    "Ontario": ["Northwest Territory", "Alberta"],
    "Greenland": ["Ontario"],
    "Quebec": ["Ontario", "Greenland"],
}

st.set_page_config(page_title="Risk Game", layout="wide")
st.title("Risk - Streamlit Edition")

if 'game' not in st.session_state:
    st.session_state['game'] = RiskGame(TERRITORY_MAP, ["Player 1", "Player 2"])
if 'selected' not in st.session_state:
    st.session_state['selected'] = []

game = st.session_state['game']
selected = st.session_state['selected']

# Board visualization using networkx
g = nx.Graph()
for t, neighbors in TERRITORY_MAP.items():
    for n in neighbors:
        g.add_edge(t, n)

pos = nx.spring_layout(g, seed=42)
fig, ax = plt.subplots(figsize=(6, 4))
colors = [game.territories[t].owner.color if game.territories[t].owner else 'gray' for t in g.nodes]

nx.draw(g, pos, with_labels=True, node_color=colors, ax=ax, node_size=1200, font_size=10)

for t in g.nodes:
    x, y = pos[t]
    ax.text(x, y+0.07, f"{game.territories[t].armies}", ha='center', va='center', fontsize=12, color='black', bbox=dict(facecolor='white', alpha=0.7, boxstyle='circle'))

st.pyplot(fig)

# Territory selection UI
st.subheader("Select Territories to Attack")
territory_names = list(game.territories.keys())
col1, col2 = st.columns(2)
with col1:
    attacker = st.selectbox("Select your territory (attacker):", territory_names, key="attacker_select")
with col2:
    defender = st.selectbox("Select target territory (defender):", territory_names, key="defender_select")

if st.button("Attack"):
    st.session_state['selected'] = [attacker, defender]
    st.success(f"Selected: {attacker} attacks {defender}")

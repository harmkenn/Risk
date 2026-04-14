import random
import streamlit as st
import json
import pandas as pd
import plotly.express as px

# ---------- LOAD GEOJSON DATA ----------
@st.cache_data
def load_geojson():
    with open("custom.geo.json", "r") as f:
        return json.load(f)

geojson_data = load_geojson()

# Extract continents as territories
TERRITORIES = {}
continent_countries = {}

for feature in geojson_data["features"]:
    continent = feature["properties"].get("continent", "Unknown")
    country_name = feature["properties"]["name"]
    
    if continent not in ["Seven seas (open ocean)", "Antarctica"]:  # Exclude non-playable areas
        if continent not in TERRITORIES:
            TERRITORIES[continent] = []
            continent_countries[continent] = []
        continent_countries[continent].append(country_name)

# For simplicity, each continent is a territory, and countries within are just visual
# In a real implementation, you'd want more granular territories
TERRITORIES = {continent: [] for continent in continent_countries.keys()}

# Define continent connections (adjacent continents)
TERRITORIES["North America"] = ["South America", "Europe", "Asia"]
TERRITORIES["South America"] = ["North America", "Africa"]
TERRITORIES["Europe"] = ["North America", "Asia", "Africa"]
TERRITORIES["Africa"] = ["Europe", "South America", "Asia"]
TERRITORIES["Asia"] = ["Europe", "Africa", "North America", "Oceania"]
TERRITORIES["Oceania"] = ["Asia"]

INITIAL_ARMIES_PER_PLAYER = 20  # for this small map


# ---------- RISK BATTLE LOGIC ----------

def roll_dice(num):
    return sorted([random.randint(1, 6) for _ in range(num)], reverse=True)


def single_round(att_armies, def_armies):
    att_dice = min(3, att_armies - 1)
    def_dice = min(2, def_armies)

    att_rolls = roll_dice(att_dice)
    def_rolls = roll_dice(def_dice)

    att_losses = 0
    def_losses = 0

    for a, d in zip(att_rolls, def_rolls):
        if a > d:
            def_losses += 1
        else:
            att_losses += 1

    return att_losses, def_losses, att_rolls, def_rolls


def simulate_attack_step(state, from_terr, to_terr):
    territories = state["territories"]
    att_owner = territories[from_terr]["owner"]
    def_owner = territories[to_terr]["owner"]

    att_armies = territories[from_terr]["armies"]
    def_armies = territories[to_terr]["armies"]

    if att_owner == def_owner:
        return "Cannot attack your own territory.", None, None

    if att_armies < 2:
        return "Attacking territory must have at least 2 armies.", None, None

    att_loss, def_loss, att_rolls, def_rolls = single_round(att_armies, def_armies)

    territories[from_terr]["armies"] -= att_loss
    territories[to_terr]["armies"] -= def_loss

    battle_log = f"Attacker rolls {att_rolls}, Defender rolls {def_rolls}. "
    battle_log += f"Attacker loses {att_loss}, Defender loses {def_loss}. "

    # Territory capture
    if territories[to_terr]["armies"] <= 0:
        territories[to_terr]["owner"] = att_owner
        move_armies = min(3, territories[from_terr]["armies"] - 1)
        if move_armies < 1:
            move_armies = 1
        territories[from_terr]["armies"] -= move_armies
        territories[to_terr]["armies"] = move_armies
        battle_log += f"{att_owner} captures {to_terr} and moves {move_armies} armies."

    return None, battle_log, (att_rolls, def_rolls)


# ---------- GAME STATE HELPERS ----------

def init_game(num_players, player_names):
    territories = {}
    terr_names = list(TERRITORIES.keys())
    random.shuffle(terr_names)

    owners = [player_names[i % num_players] for i in range(len(terr_names))]
    for name, owner in zip(terr_names, owners):
        territories[name] = {
            "owner": owner,
            "armies": 1,
            "neighbors": TERRITORIES[name],
        }

    armies_to_place = {
        player: INITIAL_ARMIES_PER_PLAYER - sum(1 for o in owners if o == player)
        for player in player_names
    }

    state = {
        "players": player_names,
        "current_player_idx": 0,
        "territories": territories,
        "phase": "setup",  # setup -> reinforce -> attack -> fortify
        "armies_to_place": armies_to_place,
        "message": "",
        "winner": None,
        "reinforced_this_turn": False,
    }
    return state


def get_current_player(state):
    return state["players"][state["current_player_idx"]]


def next_player(state):
    state["current_player_idx"] = (state["current_player_idx"] + 1) % len(state["players"])


def check_winner(state):
    owners = {t["owner"] for t in state["territories"].values()}
    if len(owners) == 1:
        state["winner"] = owners.pop()


def calc_reinforcements(state, player):
    terr_owned = sum(1 for t in state["territories"].values() if t["owner"] == player)
    return max(3, terr_owned // 3)


# ---------- PLOTLY MAP RENDERING ----------

def render_world_map(territories, current_player):
    # Create a dataframe for the choropleth
    countries_data = []
    for continent, countries in continent_countries.items():
        owner = territories.get(continent, {}).get("owner", "Neutral")
        armies = territories.get(continent, {}).get("armies", 0)
        for country in countries:
            countries_data.append({
                "country": country,
                "continent": continent,
                "owner": owner,
                "armies": armies
            })
    
    df = pd.DataFrame(countries_data)
    
    # Owner colors
    owner_colors = {
        current_player: "#4CAF50",  # current player: green
        "Player 1": "#2196F3",
        "Player 2": "#F44336", 
        "Player 3": "#9C27B0",
        "Player 4": "#FF9800",
        "Neutral": "#cccccc"
    }
    
    # Create choropleth map
    try:
        fig = px.choropleth(
            df,
            geojson=geojson_data,
            locations="country",
            featureidkey="properties.name",
            color="owner",
            color_discrete_map=owner_colors,
            hover_name="country",
            hover_data={"continent": True, "armies": True, "owner": True},
            title="World Risk Map"
        )
        
        fig.update_geos(
            showcountries=True,
            countrycolor="Black",
            showland=True,
            landcolor="lightgray"
        )
        
        fig.update_layout(
            height=500,
            margin={"r":0,"t":40,"l":0,"b":0}
        )
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating map: {e}")
        # Fallback: show territory info as text
        st.write("Territory ownership:")
        for terr_name, terr_data in territories.items():
            st.write(f"**{terr_name}**: {terr_data['owner']} ({terr_data['armies']} armies)")


# ---------- STREAMLIT UI ----------

st.set_page_config(page_title="World Risk Game", layout="wide")
st.title("World Risk-style Board Game")

if "game_state" not in st.session_state:
    st.session_state.game_state = None

# --- GAME SETUP ---

if st.session_state.game_state is None:
    st.subheader("Game setup")

    num_players = st.slider("Number of players", 2, 4, 2)
    default_names = [f"Player {i+1}" for i in range(num_players)]
    player_names = []

    for i in range(num_players):
        name = st.text_input(f"Name for Player {i+1}", value=default_names[i])
        player_names.append(name.strip() or default_names[i])

    if st.button("Start game"):
        st.session_state.game_state = init_game(num_players, player_names)
        st.rerun()
else:
    state = st.session_state.game_state

    # --- SIDEBAR: GAME INFO ---
    with st.sidebar:
        st.header("Game info")
        st.write(f"**Players:** {', '.join(state['players'])}")
        st.write(f"**Current player:** {get_current_player(state)}")
        st.write(f"**Phase:** {state['phase'].capitalize()}")

        if state["winner"]:
            st.success(f"Winner: {state['winner']}")

        if st.button("Restart game"):
            st.session_state.game_state = None
            st.rerun()

    territories = state["territories"]
    current_player = get_current_player(state)

    # --- MAP VIEW ---
    st.subheader("Map")
    render_world_map(territories, current_player)

    st.markdown("---")

    # --- TEXT BOARD VIEW (for debugging / clarity) ---
    with st.expander("Territory details"):
        cols = st.columns(3)
        terr_items = list(territories.items())
        chunk_size = (len(terr_items) + 2) // 3

        for col_idx, col in enumerate(cols):
            with col:
                for name, data in terr_items[col_idx * chunk_size:(col_idx + 1) * chunk_size]:
                    st.markdown(
                        f"**{name}** — Owner: {data['owner']}, Armies: {data['armies']}  \n"
                        f"Neighbors: {', '.join(data['neighbors'])}"
                    )

    st.markdown("---")

    current_player = get_current_player(state)

    if state["winner"]:
        st.success(f"Game over! {state['winner']} controls all territories.")
    else:
        # SETUP PHASE
        if state["phase"] == "setup":
            st.subheader("Setup phase: place initial armies")

            remaining = state["armies_to_place"][current_player]
            st.write(f"{current_player}, you have **{remaining}** armies to place.")

            owned_terr = [name for name, t in territories.items() if t["owner"] == current_player]

            if remaining > 0:
                terr_choice = st.selectbox("Choose a territory to reinforce", owned_terr, key="setup_terr")
                num_to_place = st.slider("Armies to place", 1, remaining, 1, key="setup_num")

                if st.button("Place armies"):
                    territories[terr_choice]["armies"] += num_to_place
                    state["armies_to_place"][current_player] -= num_to_place
                    st.rerun()
            else:
                st.write("No armies left to place.")
                if st.button("End setup turn"):
                    if all(v == 0 for v in state["armies_to_place"].values()):
                        state["phase"] = "reinforce"
                        reinf = calc_reinforcements(state, current_player)
                        state["armies_to_place"][current_player] = reinf
                    else:
                        next_player(state)
                    st.rerun()

        # REINFORCE PHASE
        elif state["phase"] == "reinforce":
            st.subheader("Reinforcement phase")

            remaining = state["armies_to_place"].get(current_player, 0)
            if remaining == 0:
                if not state["reinforced_this_turn"]:
                    reinf = calc_reinforcements(state, current_player)
                    state["armies_to_place"][current_player] = reinf
                    state["reinforced_this_turn"] = True
                    remaining = reinf
                else:
                    st.write("No reinforcements left.")
                    if st.button("Proceed to attack phase"):
                        state["phase"] = "attack"
                        state["reinforced_this_turn"] = False
                        st.rerun()
            else:
                st.write(f"{current_player}, you have **{remaining}** reinforcements to place.")
                owned_terr = [name for name, t in territories.items() if t["owner"] == current_player]
                terr_choice = st.selectbox("Choose a territory to reinforce", owned_terr, key="reinforce_terr")
                num_to_place = st.slider("Armies to place", 1, remaining, 1, key="reinforce_num")

                if st.button("Place reinforcements"):
                    territories[terr_choice]["armies"] += num_to_place
                    state["armies_to_place"][current_player] -= num_to_place
                    st.rerun()

        # ATTACK PHASE
        elif state["phase"] == "attack":
            st.subheader("Attack phase")

            owned_terr = [name for name, t in territories.items()
                          if t["owner"] == current_player and t["armies"] > 1]

            if not owned_terr:
                st.write("You have no territories with enough armies to attack.")
            else:
                from_terr = st.selectbox("From territory", owned_terr, key="attack_from")

                possible_targets = [
                    n for n in territories[from_terr]["neighbors"]
                    if territories[n]["owner"] != current_player
                ]

                if possible_targets:
                    to_terr = st.selectbox("Target territory", possible_targets, key="attack_to")

                    if st.button("Attack once"):
                        error, log, rolls = simulate_attack_step(state, from_terr, to_terr)
                        if error:
                            st.error(error)
                        else:
                            st.info(log)
                            check_winner(state)
                            st.rerun()
                else:
                    st.write("No enemy neighbors to attack from this territory.")

            st.markdown("----")
            if st.button("End attack phase"):
                state["phase"] = "fortify"
                st.rerun()

        # FORTIFY PHASE
        elif state["phase"] == "fortify":
            st.subheader("Fortify phase (optional)")

            owned_terr = [name for name, t in territories.items() if t["owner"] == current_player]

            from_terr = st.selectbox("Move from", owned_terr, key="fortify_from")
            to_terr_options = [n for n in territories[from_terr]["neighbors"]
                               if territories[n]["owner"] == current_player]

            if to_terr_options:
                to_terr = st.selectbox("Move to", to_terr_options, key="fortify_to")
                max_move = max(0, territories[from_terr]["armies"] - 1)
                if max_move > 0:
                    num_move = st.slider("Armies to move", 1, max_move, 1, key="fortify_num")
                    if st.button("Move armies"):
                        territories[from_terr]["armies"] -= num_move
                        territories[to_terr]["armies"] += num_move
                        st.rerun()
                else:
                    st.write("Not enough armies to move (must leave at least 1 behind).")
            else:
                st.write("No friendly neighbors to fortify.")

            if st.button("End turn"):
                next_player(state)
                state["phase"] = "reinforce"
                state["reinforced_this_turn"] = False
                st.rerun()

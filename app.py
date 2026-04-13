import random
import streamlit as st

# ---------- GAME DATA ----------

TERRITORIES = {
    "Alpha": ["Bravo", "Charlie"],
    "Bravo": ["Alpha", "Delta"],
    "Charlie": ["Alpha", "Delta", "Echo"],
    "Delta": ["Bravo", "Charlie", "Foxtrot"],
    "Echo": ["Charlie", "Foxtrot"],
    "Foxtrot": ["Delta", "Echo"],
}

INITIAL_ARMIES_PER_PLAYER = 20  # for this small map

# Approximate label positions for each territory on the SVG
TERRITORY_LABEL_POS = {
    "Alpha": (150, 135),
    "Bravo": (275, 175),
    "Charlie": (190, 220),
    "Delta": (380, 230),
    "Echo": (295, 270),
    "Foxtrot": (400, 320),
}


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


# ---------- SVG MAP RENDERING ----------

def render_svg_map(territories, current_player):
    try:
        with open("map.svg", "r") as f:
            svg = f.read()
    except FileNotFoundError:
        st.error("map.svg not found in the app directory.")
        return

    owner_colors = {
        current_player: "#4CAF50",  # current player: green
        "Player 1": "#2196F3",
        "Player 2": "#F44336",
        "Player 3": "#9C27B0",
        "Player 4": "#FF9800",
    }

    css_rules = []
    for name, data in territories.items():
        color = owner_colors.get(data["owner"], "#cccccc")
        css_rules.append(f"#{name} {{ fill: {color}; stroke: black; stroke-width: 2px; }}")

    style_block = "<style>" + " ".join(css_rules) + "</style>"
    svg = svg.replace("<svg ", "<svg ")  # no-op, just to keep structure
    svg = svg.replace(">", ">" + style_block, 1)

    # Add army labels
    label_elems = []
    for name, data in territories.items():
        if name in TERRITORY_LABEL_POS:
            x, y = TERRITORY_LABEL_POS[name]
            label_elems.append(
                f'<text x="{x}" y="{y}" text-anchor="middle" '
                f'font-size="16" font-family="Arial" fill="black">'
                f'{data["armies"]}</text>'
            )

    svg = svg.replace("</svg>", "\n" + "\n".join(label_elems) + "\n</svg>")

    st.markdown(svg, unsafe_allow_html=True)


# ---------- STREAMLIT UI ----------

st.set_page_config(page_title="Mini Risk Engine with Map", layout="wide")
st.title("Mini Risk-style Board Game (with SVG Map)")

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
    render_svg_map(territories, current_player)

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

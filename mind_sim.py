import streamlit as st
import numpy as np
import random
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# Constants
GRID_WIDTH = 30
GRID_HEIGHT = 30
MAX_ENERGY = 10.0

MOOD_DATA = {
    "happy": {"color": (0, 200, 0), "emoji": "😊"},
    "neutral": {"color": (200, 200, 0), "emoji": "😐"},
    "stressed": {"color": (200, 100, 0), "emoji": "😰"},
    "angry": {"color": (200, 0, 0), "emoji": "😡"},
}

class Creature:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.energy = random.uniform(4, 7)
        self.stress = 0.0
        self.habituation_rate = 0.95
        self.inhibition = 0.3
        self.disinhibited = False
        self.constricted = False
        self.response = 1.0
        self.mood = "neutral"

    def update(self, creatures):
        self.response *= self.habituation_rate
        if not self.disinhibited:
            self.response -= self.inhibition

        # Small random stress fluctuation up/down
        stress_change = (random.random() - 0.5) * 0.1
        self.stress = min(1.0, max(0.0, self.stress + stress_change))

        self.constricted = self.stress > 0.7
        if random.random() < 0.05:
            self.disinhibited = not self.disinhibited
            self.inhibition = 0.0 if self.disinhibited else 0.3

        self.energy -= 0.1
        if self.energy <= 0:
            self.energy = random.uniform(4, 7)
            self.stress = 0.0
            self.response = 1.0
            self.disinhibited = False
            self.inhibition = 0.3

        if self.stress < 0.3 and self.energy > 6:
            self.mood = "happy"
        elif self.stress > 0.7:
            self.mood = "angry"
        elif self.stress > 0.4:
            self.mood = "stressed"
        else:
            self.mood = "neutral"

        if not self.constricted:
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
            new_x = min(max(self.x + dx, 0), GRID_WIDTH - 1)
            new_y = min(max(self.y + dy, 0), GRID_HEIGHT - 1)
            if not any(c.x == new_x and c.y == new_y for c in creatures):
                self.x = new_x
                self.y = new_y

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def draw_grid_plotly(creatures):
    # Create empty grid background
    grid_colors = [["#1e1e1e" for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    # Fill cells with creature colors
    for c in creatures:
        mood_color = MOOD_DATA[c.mood]["color"]
        brightness = int(100 + 155 * min(1.0, c.energy / MAX_ENERGY))
        color = tuple(min(255, int(brightness * (v / 255))) for v in mood_color)
        grid_colors[c.y][c.x] = rgb_to_hex(color)

    fig = go.Figure(data=go.Heatmap(
        z=[[1]*GRID_WIDTH for _ in range(GRID_HEIGHT)],  # Dummy values to get grid shape
        x=list(range(GRID_WIDTH)),
        y=list(range(GRID_HEIGHT)),
        hoverinfo='skip',
        showscale=False,
        colorscale=[[0, '#1e1e1e'], [1, '#1e1e1e']],  # Background color fixed
        zmin=0, zmax=1,
    ))

    # Overlay colored squares for creatures using Scatter
    xs = [c.x + 0.5 for c in creatures]
    ys = [c.y + 0.5 for c in creatures]
    colors = [grid_colors[c.y][c.x] for c in creatures]

    fig.add_trace(go.Scatter(
        x=xs,
        y=ys,
        mode='markers',
        marker=dict(
            size=30,
            color=colors,
            symbol='square',
            line=dict(color='black', width=1)
        ),
        hoverinfo='text',
        text=[f"Energy: {c.energy:.1f}<br>Stress: {c.stress:.2f}<br>Mood: {c.mood}" for c in creatures],
    ))

    # Show coordinates in bottom-right corner as white text annotation
    fig.add_annotation(
        x=GRID_WIDTH - 1,
        y=GRID_HEIGHT - 1,
        text=f"0,0 bottom-left →\n{GRID_WIDTH-1},{GRID_HEIGHT-1} top-right",
        showarrow=False,
        font=dict(color="white", size=12),
        xanchor='right',
        yanchor='bottom'
    )

    fig.update_layout(
        yaxis=dict(
            autorange='reversed',
            showgrid=True,
            tickmode='linear',
            dtick=1,
            showticklabels=False,
            zeroline=False,
            gridcolor='gray',
            gridwidth=1,
            scaleanchor="x",
            scaleratio=1,
        ),
        xaxis=dict(
            showgrid=True,
            tickmode='linear',
            dtick=1,
            showticklabels=False,
            zeroline=False,
            gridcolor='gray',
            gridwidth=1,
        ),
        plot_bgcolor='#1e1e1e',
        margin=dict(l=20, r=20, t=20, b=20),
        dragmode='pan',  # enables pan on drag
    )

    fig.update_traces(hoverlabel=dict(bgcolor="black", font_size=12))

    return fig

st.set_page_config(page_title="Mind Simulation Grid", layout="wide")
st.title("🧠 Mind Simulation Sandbox")

# Initialize session state
if "creatures" not in st.session_state:
    st.session_state.creatures = [
        Creature(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
        for _ in range(10)
    ]
if "running" not in st.session_state:
    st.session_state.running = False

with st.sidebar:
    st.header("Controls")

    if st.button("Add Creature"):
        attempts = 0
        while attempts < 100:
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            if not any(c.x == x and c.y == y for c in st.session_state.creatures):
                st.session_state.creatures.append(Creature(x, y))
                break
            attempts += 1

    if st.button("Reset Creatures"):
        st.session_state.creatures = [
            Creature(random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            for _ in range(10)
        ]

    if st.session_state.running:
        if st.button("Pause"):
            st.session_state.running = False
    else:
        if st.button("Play"):
            st.session_state.running = True

# Auto-refresh and update creatures if running
if st.session_state.running:
    count = st_autorefresh(interval=500, limit=None, key="autorefresh")
    for c in st.session_state.creatures:
        c.update(st.session_state.creatures)

# Draw grid with Plotly figure (zoom/pan supported)
fig = draw_grid_plotly(st.session_state.creatures)
st.plotly_chart(fig, use_container_width=True)

# Show moods and stats
st.markdown("### Creatures' Moods")
cols = st.columns(len(st.session_state.creatures))
for idx, c in enumerate(st.session_state.creatures):
    with cols[idx]:
        st.write(f"{MOOD_DATA[c.mood]['emoji']} Energy: {c.energy:.1f}\nStress: {c.stress:.2f}")

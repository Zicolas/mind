import streamlit as st
import numpy as np
from streamlit_autorefresh import st_autorefresh

GRID_WIDTH, GRID_HEIGHT = 20, 15
PIXEL_SIZE = 20

st.title("Minimal Grid Simulation with Play/Pause")

# Initialize session state variables
if "running" not in st.session_state:
    st.session_state.running = False
if "pos" not in st.session_state:
    st.session_state.pos = 0

# Control buttons (always visible)
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("▶️ Play" if not st.session_state.running else "⏸ Pause"):
        st.session_state.running = not st.session_state.running
with col2:
    st.write("Click Play to start the simulation.")

# Autorefresh only when running
if st.session_state.running:
    st_autorefresh(interval=1000, limit=None, key="refresh")

# Update position if running
if st.session_state.running:
    st.session_state.pos = (st.session_state.pos + 1) % GRID_WIDTH

# Create empty grid and draw moving pixel
grid = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=np.uint8)
grid[GRID_HEIGHT // 2, st.session_state.pos] = [255, 0, 0]  # red pixel in middle row

# Scale grid pixels up for visibility
display_img = np.kron(grid, np.ones((PIXEL_SIZE, PIXEL_SIZE, 1), dtype=np.uint8))

# Show grid image
st.image(display_img, caption="Moving pixel grid", use_container_width=False)

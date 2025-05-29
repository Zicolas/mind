import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import random

st.set_page_config(page_title="Mind Simulator", layout="wide")
st.title("🧠 Mind Simulation Sandbox")

# --- Initialize session state ---
if "response" not in st.session_state:
    st.session_state.response = 1.0
    st.session_state.habituation = {"noise": 0, "light": 0, "pressure": 0}
    st.session_state.stress = 0.0
    st.session_state.arousal = 0.0
    st.session_state.energy = 1.0
    st.session_state.actions = []
    st.session_state.log = []
    st.session_state.t = 0

# --- Stimulus Input Buttons ---
st.subheader("Stimulate the Mind")
cols = st.columns(3)
stimulus = None
if cols[0].button("🔊 Noise"):
    stimulus = "noise"
elif cols[1].button("💡 Light"):
    stimulus = "light"
elif cols[2].button("⚡ Pressure"):
    stimulus = "pressure"

# --- Simulation Step ---
if stimulus:
    t = st.session_state.t
    st.session_state.t += 1

    # Update Habituation
    count = st.session_state.habituation[stimulus]
    decay = 0.85 ** count
    st.session_state.habituation[stimulus] += 1
    response = 1.0 * decay

    # Update stress & arousal
    st.session_state.stress = min(1.0, st.session_state.stress + random.uniform(0.05, 0.15))
    st.session_state.arousal = min(1.0, 0.6 * st.session_state.stress + random.uniform(0.0, 0.2))

    # Inhibition
    base_inhibition = 1.0 - st.session_state.arousal
    fatigue_penalty = 1.0 - st.session_state.energy
    inhibition = max(0.0, base_inhibition - fatigue_penalty)
    response *= inhibition

    # Constriction
    constricted = st.session_state.stress > 0.6 or st.session_state.energy < 0.4
    actions = ["escape"] if constricted else ["explore", "eat", "rest"]

    # Disinhibition
    disinhibited = st.session_state.arousal > 0.8 and st.session_state.energy < 0.3
    if disinhibited:
        actions = ["scream", "run", "shutdown"]
        response += 0.5
        st.session_state.energy = 1.0

    # Energy drain
    st.session_state.energy = max(0.0, st.session_state.energy - 0.1 * st.session_state.stress)

    # Log state
    st.session_state.actions.append(actions[0])
    st.session_state.log.append({
        "t": t,
        "response": response,
        "stress": st.session_state.stress,
        "arousal": st.session_state.arousal,
        "energy": st.session_state.energy,
        "action": actions[0],
        "stimulus": stimulus
    })

# --- Display Current State ---
st.subheader("🧠 Mind State")
if st.session_state.log:
    latest = st.session_state.log[-1]
    st.metric("Response", f"{latest['response']:.2f}")
    st.metric("Stress", f"{latest['stress']:.2f}")
    st.metric("Arousal", f"{latest['arousal']:.2f}")
    st.metric("Energy", f"{latest['energy']:.2f}")
    st.metric("Action", latest['action'])

# --- Live Chart ---
if st.session_state.log:
    st.subheader("📈 Dynamics Over Time")
    fig, ax = plt.subplots()
    log = st.session_state.log
    t_vals = [entry["t"] for entry in log]
    ax.plot(t_vals, [entry["response"] for entry in log], label="Response", marker='o')
    ax.plot(t_vals, [entry["stress"] for entry in log], label="Stress", linestyle="--")
    ax.plot(t_vals, [entry["arousal"] for entry in log], label="Arousal", linestyle="-.")
    ax.plot(t_vals, [entry["energy"] for entry in log], label="Energy", linestyle=":")
    ax.legend()
    ax.set_xlabel("Time")
    ax.set_ylabel("Level")
    ax.grid(True)
    st.pyplot(fig)

# --- Action Log ---
if st.session_state.log:
    st.subheader("📜 Action Log")
    for entry in reversed(st.session_state.log[-10:]):
        st.markdown(f"**t={entry['t']:2d}** | Stimulus: `{entry['stimulus']}` → Action: **{entry['action']}** | Response: {entry['response']:.2f}")

import streamlit as st
import pandas as pd
import time
import altair as alt

# --- Page Configuration ---
st.set_page_config(
    page_title="Ops Management Factory Sim",
    page_icon="🏭",
    layout="wide"
)

# --- App Title and Introduction ---
st.title("🏭 Operations Management Factory Simulation")
st.markdown("""
Welcome, Factory Manager! Your goal is to meet customer demand efficiently.
This simulation demonstrates key concepts from the **Theory of Constraints (TOC)**.
- **Takt Time**: The rate you *need* to produce to meet demand.
- **Bottleneck**: The slowest process that limits the entire factory's output.
- **Drum-Buffer-Rope (DBR)**: A TOC method to manage production flow.
    - **Drum**: The bottleneck, setting the pace for the entire system.
    - **Buffer**: A small amount of Work-in-Progress (WIP) strategically placed before the drum to ensure it's never idle.
    - **Rope**: The mechanism that releases new materials only when the drum needs them, preventing WIP overload.

**Experiment by running the simulation with and without DBR enabled!**
""")

# --- Helper Functions and Classes ---
class FactorySimulation:
    """A class to manage the state and logic of the factory simulation."""
    def __init__(self, stations, use_dbr, buffer_size):
        self.stations = stations
        self.use_dbr = use_dbr
        self.buffer_size = buffer_size

        # Find the bottleneck (drum)
        self.bottleneck_name = max(self.stations, key=lambda s: self.stations[s]['time'])
        self.bottleneck_idx = list(self.stations.keys()).index(self.bottleneck_name)

        # Initialize state
        self.reset()

    def reset(self):
        """Resets the simulation to its initial state."""
        self.time = 0
        self.units_produced = 0
        self.wip = {name: 0 for name in self.stations}
        self.station_status = {name: {'state': 'idle', 'time_left': 0} for name in self.stations}
        self.history = []
        self.log = []

    def step(self):
        """Advance the simulation by one time unit (e.g., one second)."""
        self.time += 1
        station_names = list(self.stations.keys())

        # --- Process units at each station (from end to start) ---
        for i in range(len(station_names) - 1, -1, -1):
            name = station_names[i]
            status = self.station_status[name]

            if status['state'] == 'processing':
                status['time_left'] -= 1
                if status['time_left'] <= 0:
                    status['state'] = 'idle'
                    # Move completed unit to the next station's WIP or count as finished
                    if i == len(station_names) - 1:
                        self.units_produced += 1
                        self.log.append(f"Time {self.time}: ✅ Unit finished at {name}! Total produced: {self.units_produced}")
                    else:
                        next_station_name = station_names[i+1]
                        self.wip[next_station_name] += 1
                        self.log.append(f"Time {self.time}: ➡️ Unit moved from {name} to {next_station_name} WIP")

        # --- Start processing new units (from start to end) ---
        for i in range(len(station_names)):
            name = station_names[i]
            status = self.station_status[name]
            if status['state'] == 'idle' and self.wip[name] > 0:
                self.wip[name] -= 1
                status['state'] = 'processing'
                status['time_left'] = self.stations[name]['time']
                self.log.append(f"Time {self.time}: ⚙️ {name} started processing a new unit.")


        # --- Material Release Logic (The "Rope") ---
        first_station_name = station_names[0]
        if self.use_dbr:
            # DBR Logic: Release material only if the buffer is not full
            buffer_wip = sum(self.wip[name] for name in station_names[:self.bottleneck_idx+1])
            if buffer_wip < self.buffer_size:
                 self.wip[first_station_name] += 1
                 self.log.append(f"Time {self.time}: 🪢 Rope signals release. New material enters {first_station_name}.")
        else:
            # Traditional "Push" System: Release material whenever the first station is ready
            self.wip[first_station_name] += 1
            self.log.append(f"Time {self.time}: 📥 PUSH! New material enters {first_station_name}.")

        # Record history for plotting
        history_entry = {'Time': self.time, 'Units Produced': self.units_produced}
        for name in self.stations:
            history_entry[f"WIP_{name}"] = self.wip[name]
        self.history.append(history_entry)

# --- Sidebar for Simulation Controls ---
with st.sidebar:
    st.header("⚙️ Factory Controls")

    # Factory Configuration
    st.subheader("1. Workstation Setup")
    p_time_cutting = st.slider("Cutting Time (sec/unit)", 1, 20, 5)
    p_time_welding = st.slider("Welding Time (sec/unit)", 1, 20, 10)
    p_time_painting = st.slider("Painting Time (sec/unit)", 1, 20, 7)
    p_time_assembly = st.slider("Assembly Time (sec/unit)", 1, 20, 6)

    stations = {
        "Cutting": {"time": p_time_cutting},
        "Welding": {"time": p_time_welding},
        "Painting": {"time": p_time_painting},
        "Assembly": {"time": p_time_assembly},
    }

    # Demand and Time
    st.subheader("2. Demand & Schedule")
    available_time = st.number_input("Available Work Time (seconds)", min_value=100, max_value=5000, value=1000, step=100)
    customer_demand = st.number_input("Customer Demand (units)", min_value=1, max_value=500, value=100, step=5)
    takt_time = available_time / customer_demand

    # DBR Controls
    st.subheader("3. Strategy")
    use_dbr = st.toggle("Enable Drum-Buffer-Rope (TOC)", value=False)
    buffer_size = 1
    if use_dbr:
        buffer_size = st.slider("Buffer Size (units before Bottleneck)", 1, 20, 5)

    # Simulation Speed
    st.subheader("4. Simulation Speed")
    sim_speed = st.select_slider("Animation Speed", options=["Fast", "Medium", "Slow"], value="Medium")
    speed_map = {"Fast": 0.001, "Medium": 0.01, "Slow": 0.1}
    sleep_time = speed_map[sim_speed]

    run_simulation = st.button("🚀 Run Simulation!", type="primary")

# --- Main Simulation Area ---
st.header("🏭 Factory Floor")

# --- Pre-simulation Metrics Display ---
col1, col2, col3 = st.columns(3)
bottleneck_name = max(stations, key=lambda s: stations[s]['time'])
bottleneck_time = stations[bottleneck_name]['time']

col1.metric("🎯 Takt Time", f"{takt_time:.2f} sec/unit", help="The required pace to meet demand. You must be faster than this!")
col2.metric("🐌 Bottleneck (Drum)", f"{bottleneck_name}", help=f"The slowest process, at {bottleneck_time} sec/unit. This is the 'drum' that sets the factory's pace.")
col3.metric("📈 Max Throughput", f"{3600/bottleneck_time:.1f} units/hour", help="The maximum theoretical output rate of the system, dictated by the bottleneck.")
st.divider()

if not run_simulation:
    st.info("Set your parameters in the sidebar and click 'Run Simulation!' to begin.")
    st.image("https://i.imgur.com/eB442vW.png", caption="A visual representation of a production line.")

if run_simulation:
    # --- Live Simulation Display ---
    sim = FactorySimulation(stations, use_dbr, buffer_size)
    
    # Create placeholders for dynamic updates
    station_cols = st.columns(len(stations))
    progress_bar = st.progress(0, text="Simulation Progress: 0%")
    
    placeholders = {}
    for i, name in enumerate(stations):
        with station_cols[i]:
            placeholders[name] = {
                "header": st.empty(),
                "metric": st.empty(),
                "progress": st.empty()
            }

    chart_placeholder = st.empty()
    summary_placeholder = st.empty()
    log_expander = st.expander("📜 View Simulation Log")
    log_placeholder = log_expander.empty()

    for t in range(available_time):
        sim.step()

        # Update UI periodically to avoid slowing down the browser
        if t % 5 == 0:
            progress = (t + 1) / available_time
            progress_bar.progress(progress, text=f"Simulation Progress: {int(progress * 100)}%")

            for i, name in enumerate(stations):
                is_bottleneck = " (Drum 🥁)" if name == sim.bottleneck_name else ""
                placeholders[name]["header"].markdown(f"**{i+1}. {name}{is_bottleneck}**")
                
                status = sim.station_status[name]
                wip_val = sim.wip[name]
                placeholders[name]["metric"].metric(f"WIP", f"{wip_val} units")

                if status['state'] == 'processing':
                    p_val = 1 - (status['time_left'] / stations[name]['time'])
                    placeholders[name]["progress"].progress(p_val)
                else:
                    placeholders[name]["progress"].progress(0)
            
            # Update WIP Chart
            df_history = pd.DataFrame(sim.history)
            wip_cols = [f"WIP_{s}" for s in stations]
            df_melted = df_history.melt(id_vars=['Time'], value_vars=wip_cols, var_name='Station', value_name='WIP')
            
            chart = alt.Chart(df_melted).mark_area(opacity=0.5).encode(
                x='Time',
                y=alt.Y('WIP:Q', stack='zero'),
                color='Station:N',
                tooltip=['Time', 'Station', 'WIP']
            ).properties(
                title='Work-in-Progress (WIP) Over Time'
            )
            chart_placeholder.altair_chart(chart, use_container_width=True)

            # Update Log
            log_placeholder.text_area("Log", "".join(reversed(sim.log)), height=200, key=f"log_{t}")

            time.sleep(sleep_time)

    progress_bar.progress(1.0, text="Simulation Complete!")
    
    # --- Final Results ---
    st.header("🏁 Simulation Results & Analysis")
    
    total_wip = sum(sim.wip.values())
    cycle_time = available_time / sim.units_produced if sim.units_produced > 0 else float('inf')
    
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    res_col1.metric("✅ Units Produced", f"{sim.units_produced} units")
    res_col2.metric("📦 Final WIP", f"{total_wip} units")
    res_col3.metric("⏱️ Average Cycle Time", f"{cycle_time:.2f} sec/unit")
    
    demand_met = "✔️ Yes" if sim.units_produced >= customer_demand else "❌ No"
    res_col4.metric("Met Demand?", demand_met)

    st.subheader("Analysis")
    if use_dbr:
        st.success("""
        **DBR (TOC) Analysis:**
        You likely saw much lower Work-in-Progress (WIP) and a smoother, more predictable flow. By "tying the rope" from the bottleneck (drum) to the start of the line, we only released material when the system could actually handle it. This prevents the massive pile-ups seen in traditional systems. The buffer ensured the bottleneck was almost never starved for work, maximizing the output of the entire factory. **This is a 'pull' system.**
        """)
    else:
        st.warning(f"""
        **Traditional 'Push' System Analysis:**
        Notice how WIP piled up dramatically, especially before the bottleneck station **({bottleneck_name})**? This is a classic symptom of a "push" system, where work is pushed into the line regardless of whether the next station is ready. This leads to high inventory costs, long lead times, and chaos on the factory floor. Even though you produced units, it was likely inefficient and costly.
        """)

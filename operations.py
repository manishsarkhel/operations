import streamlit as st
import pandas as pd
import altair as alt

# --- Page Configuration ---
st.set_page_config(
    page_title="Ops Factory Strategy Sim",
    page_icon="🏭",
    layout="wide"
)

# --- Core Simulation Function ---

def run_factory_simulation(stations, use_dbr, buffer_size, available_time):
    """
    Runs the full factory simulation in a single, fast batch process.
    """
    # --- Simulation State Initialization ---
    wip = {name: 0 for name in stations}
    station_status = {name: {'state': 'idle', 'time_left': 0} for name in stations}
    units_produced = 0
    history = []
    station_names = list(stations.keys())

    # Find the bottleneck (drum) for DBR logic
    bottleneck_name = max(stations, key=lambda s: stations[s]['time'])
    bottleneck_idx = station_names.index(bottleneck_name)

    # --- Main Simulation Loop ---
    for t in range(1, available_time + 1):
        # --- 1. Process units at each station (from end to start) ---
        for i in range(len(station_names) - 1, -1, -1):
            name = station_names[i]
            status = station_status[name]

            if status['state'] == 'processing':
                status['time_left'] -= 1
                if status['time_left'] <= 0:
                    status['state'] = 'idle'
                    # Move completed unit to next station or count as finished
                    if i == len(station_names) - 1:
                        units_produced += 1
                    else:
                        next_station_name = station_names[i + 1]
                        wip[next_station_name] += 1
        
        # --- 2. Start processing new units (from start to end) ---
        for i, name in enumerate(station_names):
            status = station_status[name]
            if status['state'] == 'idle' and wip[name] > 0:
                wip[name] -= 1
                status['state'] = 'processing'
                status['time_left'] = stations[name]['time']

        # --- 3. Material Release Logic (The "Rope") ---
        first_station_name = station_names[0]
        if use_dbr:
            # DBR Logic: Release material only if the buffer is not full
            buffer_wip = sum(wip[name] for name in station_names[:bottleneck_idx + 1])
            if buffer_wip < buffer_size:
                 wip[first_station_name] += 1
        else:
            # Traditional "Push" System: Release material every time step
            wip[first_station_name] += 1

        # --- 4. Record history for plotting ---
        history_entry = {'Time': t, 'Units Produced': units_produced, 'Total WIP': sum(wip.values())}
        for name in stations:
            history_entry[f"WIP_{name}"] = wip[name]
        history.append(history_entry)
        
    return pd.DataFrame(history), units_produced, sum(wip.values())


# --- UI Layout ---

st.title("🏭 Factory Strategy Simulator (Lightweight)")
st.markdown("""
Welcome, Manager! This simulation runs instantly to test different production strategies.
Your goal is to meet customer demand efficiently by configuring your factory and choosing a strategy.
- **Takt Time**: The rate you *need* to produce to meet demand.
- **Bottleneck**: The slowest process that limits your factory's output.
- **Drum-Buffer-Rope (DBR)**: A method to manage production based on your bottleneck.

Set your parameters, run the simulation, and compare the results of a traditional **'Push'** system versus a **DBR** system.
""")

# --- Sidebar for Simulation Controls ---
with st.sidebar:
    st.header("⚙️ Factory Controls")

    # 1. Workstation Setup
    st.subheader("1. Workstation Setup")
    p_time_cutting = st.slider("Cutting Time (sec/unit)", 1, 20, 5)
    p_time_welding = st.slider("Welding Time (sec/unit)", 1, 20, 10, help="Make this the longest to create a bottleneck.")
    p_time_painting = st.slider("Painting Time (sec/unit)", 1, 20, 7)
    p_time_assembly = st.slider("Assembly Time (sec/unit)", 1, 20, 6)

    stations = {
        "Cutting": {"time": p_time_cutting},
        "Welding": {"time": p_time_welding},
        "Painting": {"time": p_time_painting},
        "Assembly": {"time": p_time_assembly},
    }

    # 2. Demand & Schedule
    st.subheader("2. Demand & Schedule")
    available_time = st.number_input("Available Work Time (seconds)", min_value=100, max_value=10000, value=1000, step=100)
    customer_demand = st.number_input("Customer Demand (units)", min_value=1, max_value=1000, value=100, step=5)
    
    # 3. Strategy
    st.subheader("3. Strategy")
    use_dbr = st.toggle("Enable Drum-Buffer-Rope (TOC)", value=False)
    buffer_size = 1
    if use_dbr:
        buffer_size = st.slider("Buffer Size (units before Bottleneck)", 1, 20, 5)

# --- Main Simulation Area ---
st.header("📊 Pre-Simulation Metrics")

# --- Metrics Display ---
col1, col2, col3 = st.columns(3)
bottleneck_name = max(stations, key=lambda s: stations[s]['time'])
bottleneck_time = stations[bottleneck_name]['time']
takt_time = available_time / customer_demand if customer_demand > 0 else 0

col1.metric("🎯 Takt Time", f"{takt_time:.2f} sec/unit", help="The required pace to meet demand. Your bottleneck must be faster than this!")
col2.metric("🐌 Bottleneck (Drum)", f"{bottleneck_name} ({bottleneck_time}s)")
col3.metric("📈 Max Throughput", f"{3600/bottleneck_time:.1f} units/hour")

st.divider()

# --- Run Button ---
if st.button("🚀 Run Full Simulation", type="primary"):
    with st.spinner("Simulating full production run..."):
        results_df, final_units, final_wip = run_factory_simulation(stations, use_dbr, buffer_size, available_time)

    st.header("🏁 Simulation Results")
    
    # --- Final Results Metrics ---
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("✅ Units Produced", f"{final_units} units")
    res_col2.metric("📦 Final Total WIP", f"{final_wip} units")
    
    demand_met_text = "✔️ Yes" if final_units >= customer_demand else "❌ No"
    res_col3.metric(f"Met Demand? ({customer_demand} units)", demand_met_text)

    # --- Charts ---
    st.subheader("Performance Charts")
    
    # WIP Chart
    wip_cols = [f"WIP_{s}" for s in stations]
    df_melted = results_df.melt(id_vars=['Time'], value_vars=wip_cols, var_name='Station', value_name='WIP')
    
    chart = alt.Chart(df_melted).mark_area(opacity=0.7).encode(
        x='Time',
        y=alt.Y('WIP:Q', stack='zero'),
        color='Station:N',
        tooltip=['Time', 'Station', 'WIP']
    ).properties(
        title='Work-in-Progress (WIP) at Each Station Over Time'
    )
    st.altair_chart(chart, use_container_width=True)

    # Production Chart
    prod_chart = alt.Chart(results_df).mark_line().encode(
        x='Time',
        y='Units Produced'
    ).properties(
        title='Total Units Produced Over Time'
    )
    st.altair_chart(prod_chart, use_container_width=True)

    # --- Analysis Expander ---
    with st.expander("📝 View Detailed Analysis of Your Strategy"):
        if use_dbr:
            st.success("""
            **DBR (TOC) Analysis:**
            With DBR enabled, you should see much lower and more stable Work-in-Progress (WIP) levels, especially before the bottleneck. The "Rope" prevented the factory from being flooded with work it couldn't handle, and the "Buffer" protected the bottleneck, ensuring a smooth, predictable output. This is a highly efficient **'pull' system**.
            """)
        else:
            st.warning(f"""
            **Traditional 'Push' System Analysis:**
            Notice how WIP likely exploded, especially before the bottleneck station **({bottleneck_name})**? This is the classic result of a "push" system. Work is pushed into the line regardless of capacity, leading to high inventory costs, long lead times, and inefficiency. While you may have met demand, it was likely at a much higher operational cost.
            """)
        st.dataframe(results_df, use_container_width=True)

else:
    st.info("Configure your factory in the sidebar and click the 'Run Full Simulation' button.")

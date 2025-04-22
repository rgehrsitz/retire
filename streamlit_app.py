import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
from dateutil.relativedelta import relativedelta
import json
import os
from io import BytesIO

# Import local modules
from ui_components import (
    render_scenario_inputs, 
    render_export_options, 
    render_household_tab, 
    render_settings_tab, 
    render_help_tab
)
from retirement_model import (
    simulate_retirement, 
    calculate_age, 
    calculate_service_years
)
from scenario_manager import (
    save_scenario, 
    load_scenario, 
    get_available_scenarios
)
from plots import (
    plot_monthly_income, 
    plot_monthly_delta, 
    plot_cumulative_income, 
    plot_income_sources
)
from monte_carlo import run_monte_carlo_simulation

# Set page config
st.set_page_config(page_title="Federal Retirement Scenario Explorer", layout="wide")

# Constants
DEFAULT_COLA = 0.02
DEFAULT_TSP_GROWTH = 0.05
DEFAULT_TSP_WITHDRAW = 0.04

# Session state initialization for persistence
if 'initialized' not in st.session_state:
    st.session_state['initialized'] = True
    # Default values will be set when we define the inputs

# Check for scenario loading requests (this must be at the top level before any UI elements)
if 'load_scenario_request' in st.session_state:
    # Get the loading request details
    scenario_name = st.session_state['load_scenario_request']['name']
    session_key = st.session_state['load_scenario_request']['session_key']
    
    # Load the scenario data
    try:
        scenario_data = load_scenario(f"scenarios/{scenario_name}.json")
        # Update session state with loaded data
        st.session_state[session_key] = scenario_data
        st.session_state['scenario_loaded'] = f"Successfully loaded scenario: {scenario_name}"
        # Clear the request
        del st.session_state['load_scenario_request']
    except Exception as e:
        st.session_state['scenario_loaded'] = f"Error loading scenario: {str(e)}"
        # Clear the request on error too
        if 'load_scenario_request' in st.session_state:
            del st.session_state['load_scenario_request']

def to_excel(df):
    """Convert DataFrame to Excel bytes for download"""
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Retirement_Analysis', index=False)
    writer.close()
    processed_data = output.getvalue()
    return processed_data

# Title and description
st.title("🧮 Federal Retirement Scenario Explorer")
st.markdown("""
This tool helps federal employees model different retirement scenarios, taking into account:
- FERS/CSRS benefits
- TSP growth and withdrawals
- Social Security timing
- Tax implications
- Survivor benefits
- Health insurance costs

Compare two scenarios side-by-side or model your household's combined retirement income.
""")

# Create tabs for different views
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Individual Analysis", "Household View", "Risk Analysis", "Settings", "Help"])

with tab1:
    st.header("Scenario Comparison")
    
    # Layout columns
    col1, col2 = st.columns(2)
    
    # Render scenario inputs for A and B
    with col1:
        scenario_a = render_scenario_inputs("A", "scenario_a", DEFAULT_COLA, DEFAULT_TSP_GROWTH, DEFAULT_TSP_WITHDRAW)
        
    with col2:
        scenario_b = render_scenario_inputs("B", "scenario_b", DEFAULT_COLA, DEFAULT_TSP_GROWTH, DEFAULT_TSP_WITHDRAW)
    
    # Run simulations
    # Create copies of the scenario dictionaries to avoid modifying the original
    scenario_a_sim = scenario_a.copy()
    scenario_b_sim = scenario_b.copy()
    
    # Add current salary to the scenarios
    if "current_salary" not in scenario_a_sim:
        scenario_a_sim["current_salary"] = st.session_state.get("scenario_a", {}).get("current_salary", scenario_a["high3"])
    
    if "current_salary" not in scenario_b_sim:
        scenario_b_sim["current_salary"] = st.session_state.get("scenario_b", {}).get("current_salary", scenario_b["high3"])
    
    # Add TSP fund allocation to scenario A
    scenario_a_sim["tsp_fund_allocation"] = {
        "g_fund_pct": st.session_state.get("scenario_a", {}).get("g_fund_pct", 20),
        "f_fund_pct": st.session_state.get("scenario_a", {}).get("f_fund_pct", 10),
        "c_fund_pct": st.session_state.get("scenario_a", {}).get("c_fund_pct", 40),
        "s_fund_pct": st.session_state.get("scenario_a", {}).get("s_fund_pct", 20),
        "i_fund_pct": st.session_state.get("scenario_a", {}).get("i_fund_pct", 10)
    }
    scenario_a_sim["use_fund_allocation"] = st.session_state.get("scenario_a", {}).get("use_fund_allocation", False)
    
    # Add TSP fund allocation to scenario B
    scenario_b_sim["tsp_fund_allocation"] = {
        "g_fund_pct": st.session_state.get("scenario_b", {}).get("g_fund_pct", 20),
        "f_fund_pct": st.session_state.get("scenario_b", {}).get("f_fund_pct", 10),
        "c_fund_pct": st.session_state.get("scenario_b", {}).get("c_fund_pct", 40),
        "s_fund_pct": st.session_state.get("scenario_b", {}).get("s_fund_pct", 20),
        "i_fund_pct": st.session_state.get("scenario_b", {}).get("i_fund_pct", 10)
    }
    scenario_b_sim["use_fund_allocation"] = st.session_state.get("scenario_b", {}).get("use_fund_allocation", False)
    
    # Run the simulations with the updated scenario dictionaries
    df_a = simulate_retirement(**scenario_a_sim)
    df_b = simulate_retirement(**scenario_b_sim)
    
    # Calculate dates for Social Security start
    ss_date_a = scenario_a["birthdate"] + relativedelta(years=scenario_a["ss_start_age"])
    ss_date_b = scenario_b["birthdate"] + relativedelta(years=scenario_b["ss_start_age"])
    
    # Calculate cumulative income for both scenarios
    df_a["Cumulative_Income"] = df_a["Total_Income"].cumsum()
    df_b["Cumulative_Income"] = df_b["Total_Income"].cumsum()
    
    # Calculate monthly delta
    delta_df = pd.DataFrame({
        "Date": df_a["Date"],
        "Monthly_Delta": df_b["Total_Income"] - df_a["Total_Income"]
    })
    
    # Find breakeven point
    delta_cum = df_b["Cumulative_Income"] - df_a["Cumulative_Income"]
    breakeven_idx = None
    breakeven_date = None
    breakeven_value = None
    breakeven_summary = None
    
    if (delta_cum <= 0).any() and (delta_cum >= 0).any():
        # There is a crossover point
        for i in range(1, len(delta_cum)):
            if (delta_cum.iloc[i-1] <= 0 and delta_cum.iloc[i] > 0) or (delta_cum.iloc[i-1] >= 0 and delta_cum.iloc[i] < 0):
                breakeven_idx = i
                break
        
        if breakeven_idx:
            breakeven_date = df_a["Date"].iloc[breakeven_idx]
            breakeven_value = df_a["Cumulative_Income"].iloc[breakeven_idx]
            
            # Determine which scenario overtakes
            if delta_cum.iloc[breakeven_idx] > 0:
                overtaking_scenario = "B"
                trailing_scenario = "A"
            else:
                overtaking_scenario = "A"
                trailing_scenario = "B"
            
            # Create breakeven summary
            breakeven_summary = f"Scenario {overtaking_scenario} overtakes Scenario {trailing_scenario} in {breakeven_date.strftime('%b %Y')}, with a cumulative difference of ${abs(delta_cum.iloc[breakeven_idx]):,.2f}"
    
    # Display Monthly Income Comparison
    st.subheader("📈 Monthly Income Comparison")
    
    # Show breakeven point summary if exists
    if breakeven_summary:
        st.success(breakeven_summary)
    
    # Create charts with Plotly
    fig1 = plot_monthly_income(df_a, df_b, 
                              scenario_a["retire_date"], scenario_b["retire_date"], 
                              ss_date_a, ss_date_b, use_plotly=True)
    st.plotly_chart(fig1, use_container_width=True)
    
    # Monthly Income Delta
    st.subheader("📊 Monthly Income Delta (Scenario B - Scenario A)")
    fig2 = plot_monthly_delta(delta_df, 
                             scenario_a["retire_date"], scenario_b["retire_date"], 
                             use_plotly=True)
    st.plotly_chart(fig2, use_container_width=True)
    
    # Cumulative Income
    st.subheader("📈 Cumulative Income Comparison")
    fig3 = plot_cumulative_income(df_a, df_b, 
                                 scenario_a["retire_date"], scenario_b["retire_date"], 
                                 breakeven_date, breakeven_value, breakeven_idx,
                                 use_plotly=True)
    st.plotly_chart(fig3, use_container_width=True)
    
    # Income Source Breakdown (Stacked Area Charts)
    st.subheader("💰 Income Source Breakdown")
    
    # Radio button to select which scenario to display
    scenario_choice = st.radio("Select scenario to display", ["Scenario A", "Scenario B"])
    
    if scenario_choice == "Scenario A":
        df_stacked = df_a
        retire_date = scenario_a["retire_date"]
        ss_date = ss_date_a
    else:
        df_stacked = df_b
        retire_date = scenario_b["retire_date"]
        ss_date = ss_date_b
    
    fig4 = plot_income_sources(df_stacked, retire_date, ss_date, scenario_choice, use_plotly=True)
    st.plotly_chart(fig4, use_container_width=True)
    
    # Export Options
    st.subheader("📋 Export Data")
    render_export_options(df_a, df_b, to_excel)
    
    # Data Tables (Expandable)
    with st.expander("View Raw Data Tables"):
        st.write("Scenario A")
        st.dataframe(df_a)
        st.write("Scenario B")
        st.dataframe(df_b)
        st.write("Combined")
        df_combined = pd.DataFrame({
            "Date": df_a["Date"],
            "Combined_Total_Income": df_a["Total_Income"] + df_b["Total_Income"],
            "Combined_Cumulative_Income": df_a["Cumulative_Income"] + df_b["Cumulative_Income"]
        })
        st.dataframe(df_combined)

# Render other tabs
with tab2:
    render_household_tab(df_a, df_b, 
                        scenario_a["retire_date"], scenario_b["retire_date"], 
                        ss_date_a, ss_date_b)

with tab3:
    st.header("🎯 Monte Carlo Risk Analysis")
    
    # Select scenario to analyze
    scenario_choice = st.selectbox(
        "Select scenario to analyze",
        ["Scenario A", "Scenario B"]
    )
    
    scenario = scenario_a if scenario_choice == "Scenario A" else scenario_b
    
    st.subheader("Market Variability Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # COLA variability
        cola_mean = st.slider(
            "Average Annual COLA (%)", 
            min_value=0.0, 
            max_value=0.04, 
            value=scenario["cola"],
            step=0.001,
            format="%.3f"
        )
        
        cola_std = st.slider(
            "COLA Variability (std dev %)", 
            min_value=0.001, 
            max_value=0.02, 
            value=0.005,
            step=0.001,
            format="%.3f"
        )
    
    with col2:
        # TSP growth variability
        tsp_growth_mean = st.slider(
            "Average TSP Growth Rate (%)", 
            min_value=0.0, 
            max_value=0.12, 
            value=scenario["tsp_growth"],
            step=0.001,
            format="%.3f"
        )
        
        tsp_growth_std = st.slider(
            "TSP Growth Variability (std dev %)", 
            min_value=0.01, 
            max_value=0.20, 
            value=0.10,
            step=0.01,
            format="%.2f"
        )
    
    # Number of simulations
    num_simulations = st.slider(
        "Number of Simulations",
        min_value=10,
        max_value=1000,
        value=100,
        step=10
    )
    
    if st.button("Run Monte Carlo Simulation"):
        with st.spinner("Running simulations..."):
            mc_scenario = scenario.copy()
            if "cola" in mc_scenario:
                del mc_scenario["cola"]
            if "tsp_growth" in mc_scenario:
                del mc_scenario["tsp_growth"]
            mc_results, mc_metrics = run_monte_carlo_simulation(
                **mc_scenario,
                cola_mean=cola_mean,
                cola_std=cola_std,
                tsp_growth_mean=tsp_growth_mean,
                tsp_growth_std=tsp_growth_std,
                num_simulations=num_simulations
            )
            clean_results = mc_results.dropna(axis=0, how='any')
            try:
                import plotly.graph_objects as go
                fig = go.Figure()
                for percentile, color in [
                    (5, "rgba(231,107,243,0.2)"),
                    (25, "rgba(231,107,243,0.3)"),
                    (50, "rgba(231,107,243,1.0)"),
                    (75, "rgba(231,107,243,0.3)"),
                    (95, "rgba(231,107,243,0.2)")
                ]:
                    fig.add_trace(go.Scatter(
                        x=mc_results.index,
                        y=mc_results[f"p{percentile}"],
                        mode='lines',
                        line=dict(color=color, width=2 if percentile == 50 else 1),
                        name=f"{percentile}th Percentile"
                    ))
                fig.update_layout(
                    title="Monthly Income Projections (with uncertainty)",
                    xaxis_title="Date",
                    yaxis_title="Monthly Income ($)",
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True)

            except ImportError:
                import matplotlib.pyplot as plt
                fig, ax = plt.subplots(figsize=(10, 6))
                clean_results = mc_results.dropna(axis=0, how='any')
                for percentile, alpha in [(5, 0.2), (25, 0.4), (50, 1.0), (75, 0.4), (95, 0.2)]:
                    ax.plot(clean_results.index, 
                            clean_results[f"p{percentile}"], 
                            alpha=alpha,
                            linewidth=2 if percentile == 50 else 1,
                            label=f"{percentile}th Percentile")
                ax.set_title("Monthly Income Projections (with uncertainty)")
                ax.set_xlabel("Date")
                ax.set_ylabel("Monthly Income ($)")
                ax.legend()
                ax.grid(True)
                st.pyplot(fig)

            # Summary statistics
            st.subheader("Key Insights")
            
            # Find retirement month index (might be different than before with variable simulation length)
            # We'll use index 12 as a proxy for about a year into retirement if we have enough data points
            start_idx = min(12, len(clean_results) - 1)
            # For 10 years after retirement - use available data or max
            ten_year_idx = min(120, len(clean_results) - 1)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Median Monthly Income at Retirement", 
                    f"${clean_results['p50'].iloc[start_idx]:,.2f}"
                )
                
                retirement_income = clean_results['p50'].iloc[start_idx]
                ten_year_income = clean_results['p50'].iloc[ten_year_idx]
                percentage_change = ((ten_year_income - retirement_income) / retirement_income) * 100
                
                st.metric(
                    f"Income ({ten_year_idx//12} years after retirement)",
                    f"${ten_year_income:,.2f}",
                    f"{percentage_change:.1f}%"
                )
            
            with col2:
                st.metric(
                    "Worst Case (5th percentile)",
                    f"${clean_results['p5'].iloc[ten_year_idx]:,.2f}",
                    f"{(clean_results['p5'].iloc[ten_year_idx] - retirement_income) / retirement_income * 100:.1f}%"
                )
                
                st.metric(
                    "Best Case (95th percentile)",
                    f"${clean_results['p95'].iloc[ten_year_idx]:,.2f}", 
                    f"{(clean_results['p95'].iloc[ten_year_idx] - retirement_income) / retirement_income * 100:.1f}%"
                )
            
            # Risk assessment
            st.markdown("### Risk Assessment")
            
            risk_threshold = clean_results['p50'].iloc[start_idx] * 0.8  # 80% of starting income
            months_below_threshold = (clean_results['p25'] < risk_threshold).sum()
            
            if months_below_threshold > 0:
                st.warning(f"There is a 25% chance your income could fall below 80% of your starting retirement income for {months_below_threshold} months.")
            else:
                st.success("Your plan appears robust. Even in the 25th percentile scenario, your income stays above 80% of your starting retirement income.")
                
            # Download link for Monte Carlo data
            st.download_button(
                "Download Monte Carlo Results",
                data=to_excel(mc_results),
                file_name="monte_carlo_simulation.xlsx",
                mime="application/vnd.ms-excel"
            )

with tab4:
    render_settings_tab()

with tab5:
    render_help_tab()

# Add footer
st.markdown("---")
st.caption("Built with ❤️ using Streamlit. Designed specifically for federal employees planning retirement.")
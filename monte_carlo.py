import numpy as np
import pandas as pd
import datetime as dt
from dateutil.relativedelta import relativedelta
from retirement_model import simulate_retirement

def run_monte_carlo_simulation(
    birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
    ss_start_age, survivor_option, cola_mean, cola_std, tsp_growth_mean, tsp_growth_std, 
    tsp_withdraw, pa_resident, fehb_premium, filing_status="single",
    num_simulations=100, sim_years=25
):
    """
    Run Monte Carlo simulation for retirement planning
    
    Parameters:
    - All the standard parameters for simulate_retirement
    - cola_mean: Mean annual COLA percentage (e.g., 0.02 for 2%)
    - cola_std: Standard deviation for COLA (e.g., 0.005 for 0.5%)
    - tsp_growth_mean: Mean annual TSP growth rate (e.g., 0.05 for 5%)
    - tsp_growth_std: Standard deviation for TSP growth (e.g., 0.10 for 10%)
    - num_simulations: Number of simulation runs (default: 100)
    - sim_years: Number of years to simulate after retirement (default: 25)
    
    Returns:
    - DataFrame with retirement dates as index and percentile columns for each month
    """
    # Initialize DataFrame to store results
    first_sim = simulate_retirement(
        birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
        ss_start_age, survivor_option, cola_mean, tsp_growth_mean, tsp_withdraw,
        pa_resident, fehb_premium, filing_status, sim_years
    )
    
    # Create dates index
    dates = first_sim["Date"]
    
    # Initialize results matrix
    results = np.zeros((len(dates), num_simulations))
    
    # Run simulations
    for i in range(num_simulations):
        # Sample growth and COLA rates from normal distributions
        cola = np.random.normal(cola_mean, cola_std)
        cola = max(0, cola)  # Ensure non-negative COLA
        
        tsp_growth = np.random.normal(tsp_growth_mean, tsp_growth_std)
        
        # Run simulation with sampled parameters
        sim_df = simulate_retirement(
            birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
            ss_start_age, survivor_option, cola, tsp_growth, tsp_withdraw,
            pa_resident, fehb_premium, filing_status, sim_years
        )
        
        # Store total income in results matrix
        results[:, i] = sim_df["Total_Income"]
    
    # Calculate percentiles
    percentiles = [5, 10, 25, 50, 75, 90, 95]
    percentile_columns = {f"p{p}": [] for p in percentiles}
    
    for row_idx in range(results.shape[0]):
        row_data = results[row_idx, :]
        for p in percentiles:
            percentile_columns[f"p{p}"].append(np.percentile(row_data, p))
    
    # Create DataFrame with results
    df_results = pd.DataFrame(index=dates)
    for col, values in percentile_columns.items():
        df_results[col] = values
    
    return df_results

def generate_scenario_summary(mc_results, retirement_date, social_security_date):
    """Generate a summary of Monte Carlo simulation results"""
    # Extract key dates for analysis
    retirement_idx = mc_results.index.get_loc(retirement_date, method='nearest')
    if social_security_date >= mc_results.index[0]:
        ss_idx = mc_results.index.get_loc(social_security_date, method='nearest')
    else:
        ss_idx = None
    
    # 10 years after retirement
    ten_year_date = retirement_date + relativedelta(years=10)
    if ten_year_date <= mc_results.index[-1]:
        ten_year_idx = mc_results.index.get_loc(ten_year_date, method='nearest')
    else:
        ten_year_idx = len(mc_results) - 1
    
    # Last date in simulation
    last_idx = len(mc_results) - 1
    
    # Get values at key points
    summary = {
        "At Retirement": {
            "Date": mc_results.index[retirement_idx],
            "Median Monthly Income": mc_results["p50"].iloc[retirement_idx],
            "Lower Range (10%)": mc_results["p10"].iloc[retirement_idx],
            "Upper Range (90%)": mc_results["p90"].iloc[retirement_idx]
        },
        "10 Years After Retirement": {
            "Date": mc_results.index[ten_year_idx],
            "Median Monthly Income": mc_results["p50"].iloc[ten_year_idx],
            "Lower Range (10%)": mc_results["p10"].iloc[ten_year_idx],
            "Upper Range (90%)": mc_results["p90"].iloc[ten_year_idx]
        },
        "End of Simulation": {
            "Date": mc_results.index[last_idx],
            "Median Monthly Income": mc_results["p50"].iloc[last_idx],
            "Lower Range (10%)": mc_results["p10"].iloc[last_idx],
            "Upper Range (90%)": mc_results["p90"].iloc[last_idx]
        }
    }
    
    # Add Social Security start if applicable
    if ss_idx is not None:
        summary["At Social Security Start"] = {
            "Date": mc_results.index[ss_idx],
            "Median Monthly Income": mc_results["p50"].iloc[ss_idx],
            "Lower Range (10%)": mc_results["p10"].iloc[ss_idx],
            "Upper Range (90%)": mc_results["p90"].iloc[ss_idx]
        }
    
    return summary

def calculate_risk_metrics(mc_results, starting_income):
    """Calculate risk metrics from Monte Carlo results"""
    # Probability of income falling below starting income
    below_start = (mc_results["p50"] < starting_income).mean() * 100
    
    # Worst case income drop (5th percentile)
    min_income_p5 = mc_results["p5"].min()
    max_drop_p5 = ((starting_income - min_income_p5) / starting_income) * 100
    
    # Income volatility (standard deviation of median income)
    volatility = mc_results["p50"].std()
    
    # Risk of significant income drop (>20% from starting)
    significant_drop = (mc_results["p25"] < (starting_income * 0.8)).mean() * 100
    
    return {
        "Probability of Income Below Starting (%)": below_start,
        "Maximum Income Drop - 5th Percentile (%)": max_drop_p5,
        "Income Volatility ($)": volatility,
        "Risk of Significant Income Drop (>20%) (%)": significant_drop
    }

def run_stress_tests(
    birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
    ss_start_age, survivor_option, cola_mean, tsp_growth_mean, tsp_withdraw, 
    pa_resident, fehb_premium, filing_status="single"
):
    """Run stress tests with different market scenarios"""
    
    results = {}
    
    # Best case scenario
    results["best_case"] = simulate_retirement(
        birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
        ss_start_age, survivor_option, cola_mean + 0.005, tsp_growth_mean + 0.03, tsp_withdraw,
        pa_resident, fehb_premium, filing_status
    )
    
    # Average case scenario (baseline)
    results["average_case"] = simulate_retirement(
        birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
        ss_start_age, survivor_option, cola_mean, tsp_growth_mean, tsp_withdraw,
        pa_resident, fehb_premium, filing_status
    )
    
    # Worst case scenario
    results["worst_case"] = simulate_retirement(
        birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
        ss_start_age, survivor_option, cola_mean - 0.005, tsp_growth_mean - 0.03, tsp_withdraw,
        pa_resident, fehb_premium, filing_status
    )
    
    return results

def calculate_tsp_depletion_risk(mc_results, tsp_threshold=1000):
    """Calculate risk of TSP balance falling below threshold"""
    below_threshold_count = sum(1 for sim in mc_results if min(sim["TSP_Balance"]) < tsp_threshold)
    depletion_risk = below_threshold_count / len(mc_results) * 100
    return depletion_risk

def run_monte_carlo_with_tsp_tracking(
    birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
    ss_start_age, survivor_option, cola_mean, cola_std, tsp_growth_mean, tsp_growth_std, 
    tsp_withdraw, pa_resident, fehb_premium, filing_status="single",
    num_simulations=100, sim_years=25
):
    """Run Monte Carlo simulations with TSP balance tracking"""
    # Store full simulation results to track TSP balances
    simulations = []
    
    # Run simulations
    for i in range(num_simulations):
        # Sample growth and COLA rates from normal distributions
        cola = np.random.normal(cola_mean, cola_std)
        cola = max(0, cola)  # Ensure non-negative COLA
        
        tsp_growth = np.random.normal(tsp_growth_mean, tsp_growth_std)
        
        # Run simulation with sampled parameters
        sim_df = simulate_retirement(
            birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
            ss_start_age, survivor_option, cola, tsp_growth, tsp_withdraw,
            pa_resident, fehb_premium, filing_status, sim_years
        )
        
        # Store full simulation result
        simulations.append(sim_df)
    
    return simulations

def run_sensitivity_analysis(
    birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
    ss_start_age, survivor_option, cola_mean, tsp_growth_mean, tsp_withdraw, 
    pa_resident, fehb_premium, filing_status="single",
    parameter_ranges=None
):
    """Run sensitivity analysis by varying one parameter at a time"""
    if parameter_ranges is None:
        # Default parameter ranges to analyze
        parameter_ranges = {
            "cola": [cola_mean - 0.01, cola_mean, cola_mean + 0.01],
            "tsp_growth": [tsp_growth_mean - 0.02, tsp_growth_mean, tsp_growth_mean + 0.02],
            "tsp_withdraw": [tsp_withdraw * 0.75, tsp_withdraw, tsp_withdraw * 1.25],
            "retire_delay_years": [0, 1, 2]
        }
    
    results = {
        "cola": {},
        "tsp_growth": {},
        "tsp_withdraw": {},
        "retire_delay_years": {}
    }
    
    # Base case simulation
    base_case = simulate_retirement(
        birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
        ss_start_age, survivor_option, cola_mean, tsp_growth_mean, tsp_withdraw,
        pa_resident, fehb_premium, filing_status
    )
    
    results["base_case"] = base_case
    
    # Test COLA variations
    for cola in parameter_ranges["cola"]:
        sim_df = simulate_retirement(
            birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
            ss_start_age, survivor_option, cola, tsp_growth_mean, tsp_withdraw,
            pa_resident, fehb_premium, filing_status
        )
        results["cola"][cola] = sim_df
    
    # Test TSP growth variations
    for growth in parameter_ranges["tsp_growth"]:
        sim_df = simulate_retirement(
            birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
            ss_start_age, survivor_option, cola_mean, growth, tsp_withdraw,
            pa_resident, fehb_premium, filing_status
        )
        results["tsp_growth"][growth] = sim_df
    
    # Test TSP withdrawal rate variations
    for withdraw in parameter_ranges["tsp_withdraw"]:
        sim_df = simulate_retirement(
            birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
            ss_start_age, survivor_option, cola_mean, tsp_growth_mean, withdraw,
            pa_resident, fehb_premium, filing_status
        )
        results["tsp_withdraw"][withdraw] = sim_df
    
    # Test retirement date variations
    for years in parameter_ranges["retire_delay_years"]:
        delayed_retire_date = retire_date + relativedelta(years=years)
        sim_df = simulate_retirement(
            birthdate, start_date, delayed_retire_date, high3, tsp_start, sick_leave_hours,
            ss_start_age, survivor_option, cola_mean, tsp_growth_mean, tsp_withdraw,
            pa_resident, fehb_premium, filing_status
        )
        results["retire_delay_years"][years] = sim_df
    
    return results
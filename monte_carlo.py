import numpy as np
import pandas as pd
import datetime as dt
from dateutil.relativedelta import relativedelta
from retirement_model import simulate_retirement

def run_monte_carlo_simulation(
    birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
    ss_start_age, survivor_option, cola_mean, cola_std, tsp_growth_mean, tsp_growth_std, 
    tsp_withdraw, pa_resident, fehb_premium, filing_status="single",
    num_simulations=100, sim_years=25, bi_weekly_tsp_contribution=0, 
    matching_contribution=True, include_medicare=True, fehb_growth_rate=0.05,
    tsp_fund_allocation=None, use_fund_allocation=False,
    cola_dist='normal', tsp_growth_dist='normal', random_seed=None,
    scenario_label=None, tsp_depletion_threshold=1000, track_tsp=True, return_full_paths=False,
    withdrawal_strategy="Greater of Both",
    oasdi_rate=6.2, fers_rate=4.4, medicare_rate=1.45, fegli=0.0, other_deductions=0.0
):
    """
    Run Monte Carlo simulation for retirement planning (enhanced version).
    - Vectorized year-by-year sampling for COLA and TSP growth.
    - Parallel execution for speed.
    - User-defined distributions (normal, lognormal, or custom callable).
    - Tracks TSP balances and depletion risk.
    - Robust error handling and reproducibility (random_seed).
    - Scenario labeling for traceability.
    - Returns: (df_results, metrics_dict)
    """
    import concurrent.futures
    import traceback
    rng = np.random.default_rng(random_seed)

    def sample_dist(dist, mean, std, shape):
        if callable(dist):
            return dist(mean, std, shape)
        if dist == 'normal':
            return rng.normal(mean, std, shape)
        if dist == 'lognormal':
            sigma2 = np.log(1 + (std/mean)**2)
            mu = np.log(mean) - 0.5*sigma2
            return rng.lognormal(mu, np.sqrt(sigma2), shape)
        raise ValueError(f"Unknown distribution: {dist}")

    # Get dates index from a single baseline simulation (must be before n_months)
    first_sim = simulate_retirement(
        birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
        ss_start_age, survivor_option, cola_mean, tsp_growth_mean, tsp_withdraw,
        withdrawal_strategy=withdrawal_strategy,
        pa_resident=pa_resident, fehb_premium=fehb_premium, filing_status=filing_status, sim_years=sim_years,
        bi_weekly_tsp_contribution=bi_weekly_tsp_contribution,
        matching_contribution=matching_contribution,
        include_medicare=include_medicare,
        fehb_growth_rate=fehb_growth_rate,
        tsp_fund_allocation=tsp_fund_allocation,
        use_fund_allocation=use_fund_allocation
    )
    dates = first_sim["Date"]
    n_months = len(dates)

    cola_samples = sample_dist(cola_dist, cola_mean, cola_std, (num_simulations, n_months))
    tsp_growth_samples = sample_dist(tsp_growth_dist, tsp_growth_mean, tsp_growth_std, (num_simulations, n_months))
    # Ensure no negative COLA or TSP growth values
    cola_samples = np.clip(cola_samples, 0, None)
    tsp_growth_samples = np.clip(tsp_growth_samples, 0, None)

    income_results = np.zeros((n_months, num_simulations))
    tsp_results = np.zeros((n_months, num_simulations)) if track_tsp else None
    depletion_flags = np.zeros(num_simulations, dtype=bool)
    error_log = []

    def run_single_sim(i):
        try:
            cola_path = cola_samples[i, :n_months]
            tsp_growth_path = tsp_growth_samples[i, :n_months]
            sim_df = simulate_retirement(
                birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
                ss_start_age, survivor_option, cola_path, tsp_growth_path, tsp_withdraw,
                withdrawal_strategy=withdrawal_strategy,
                pa_resident=pa_resident, fehb_premium=fehb_premium, filing_status=filing_status, sim_years=sim_years,
                bi_weekly_tsp_contribution=bi_weekly_tsp_contribution,
                matching_contribution=matching_contribution,
                include_medicare=include_medicare,
                fehb_growth_rate=fehb_growth_rate,
                tsp_fund_allocation=tsp_fund_allocation,
                use_fund_allocation=use_fund_allocation,
                oasdi_rate=oasdi_rate, fers_rate=fers_rate, medicare_rate=medicare_rate,
                fegli=fegli, other_deductions=other_deductions
            )
            income = sim_df["Total_Income"].to_numpy()
            if track_tsp:
                tsp_bal = sim_df["TSP_Balance"].to_numpy()
                if (tsp_bal < tsp_depletion_threshold).any():
                    depletion_flags[i] = True
                return income, tsp_bal, None
            else:
                return income, None, None
        except Exception as e:
            tb = traceback.format_exc()
            return None, None, f"Simulation {i} failed: {e}\n{tb}"

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_single_sim, i) for i in range(num_simulations)]
        for i, fut in enumerate(concurrent.futures.as_completed(futures)):
            income, tsp_bal, err = fut.result()
            if err:
                error_log.append(err)
                continue
            income_results[:, i] = income
            if track_tsp:
                tsp_results[:, i] = tsp_bal

    percentiles = [5, 10, 25, 50, 75, 90, 95]
    percentile_columns = {f"p{p}": np.percentile(income_results, p, axis=1) for p in percentiles}
    tsp_percentile_columns = {f"tsp_p{p}": np.percentile(tsp_results, p, axis=1) for p in percentiles} if track_tsp else {}

    # Get dates index from a single baseline simulation
    first_sim = simulate_retirement(
        birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
        ss_start_age, survivor_option, cola_mean, tsp_growth_mean, tsp_withdraw,
        withdrawal_strategy=withdrawal_strategy,
        pa_resident=pa_resident, fehb_premium=fehb_premium, filing_status=filing_status, sim_years=sim_years,
        bi_weekly_tsp_contribution=bi_weekly_tsp_contribution,
        matching_contribution=matching_contribution,
        include_medicare=include_medicare,
        fehb_growth_rate=fehb_growth_rate,
        tsp_fund_allocation=tsp_fund_allocation,
        use_fund_allocation=use_fund_allocation
    )
    dates = first_sim["Date"]

    df_results = pd.DataFrame(index=dates)
    for col, values in percentile_columns.items():
        df_results[col] = values
    for col, values in tsp_percentile_columns.items():
        df_results[col] = values

    metrics = {
        "tsp_depletion_risk": depletion_flags.mean() * 100 if track_tsp else None,
        "error_log": error_log,
        "scenario_label": scenario_label,
        "random_seed": random_seed,
        "max_drawdown": float(np.min(percentile_columns["p5"])),
        "volatility": float(np.std(percentile_columns["p50"]))
    }
    if return_full_paths:
        metrics["all_income_paths"] = income_results
        if track_tsp:
            metrics["all_tsp_paths"] = tsp_results
    return df_results, metrics

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
    pa_resident, fehb_premium, filing_status="single", 
    bi_weekly_tsp_contribution=0, matching_contribution=True, 
    include_medicare=True, fehb_growth_rate=0.05,
    tsp_fund_allocation=None, use_fund_allocation=False
):
    """Run stress tests with different market scenarios"""
    
    results = {}
    
    # Best case scenario
    results["best_case"] = simulate_retirement(
        birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
        ss_start_age, survivor_option, cola_mean + 0.005, tsp_growth_mean + 0.03, tsp_withdraw,
        pa_resident, fehb_premium, filing_status,
        bi_weekly_tsp_contribution=bi_weekly_tsp_contribution,
        matching_contribution=matching_contribution,
        include_medicare=include_medicare,
        fehb_growth_rate=fehb_growth_rate,
        tsp_fund_allocation=tsp_fund_allocation,
        use_fund_allocation=use_fund_allocation
    )
    
    # Average case scenario (baseline)
    results["average_case"] = simulate_retirement(
        birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
        ss_start_age, survivor_option, cola_mean, tsp_growth_mean, tsp_withdraw,
        pa_resident, fehb_premium, filing_status,
        bi_weekly_tsp_contribution=bi_weekly_tsp_contribution,
        matching_contribution=matching_contribution,
        include_medicare=include_medicare,
        fehb_growth_rate=fehb_growth_rate,
        tsp_fund_allocation=tsp_fund_allocation,
        use_fund_allocation=use_fund_allocation
    )
    
    # Worst case scenario
    results["worst_case"] = simulate_retirement(
        birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
        ss_start_age, survivor_option, cola_mean - 0.005, tsp_growth_mean - 0.03, tsp_withdraw,
        pa_resident, fehb_premium, filing_status,
        bi_weekly_tsp_contribution=bi_weekly_tsp_contribution,
        matching_contribution=matching_contribution,
        include_medicare=include_medicare,
        fehb_growth_rate=fehb_growth_rate,
        tsp_fund_allocation=tsp_fund_allocation,
        use_fund_allocation=use_fund_allocation
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
    num_simulations=100, sim_years=25, bi_weekly_tsp_contribution=0, 
    matching_contribution=True, include_medicare=True, fehb_growth_rate=0.05,
    tsp_fund_allocation=None, use_fund_allocation=False
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
            pa_resident, fehb_premium, filing_status, sim_years,
            bi_weekly_tsp_contribution=bi_weekly_tsp_contribution,
            matching_contribution=matching_contribution,
            include_medicare=include_medicare,
            fehb_growth_rate=fehb_growth_rate,
            tsp_fund_allocation=tsp_fund_allocation,
            use_fund_allocation=use_fund_allocation
        )
        
        # Store full simulation result
        simulations.append(sim_df)
    
    return simulations

def run_sensitivity_analysis(
    birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
    ss_start_age, survivor_option, cola_mean, tsp_growth_mean, tsp_withdraw, 
    pa_resident, fehb_premium, filing_status="single", bi_weekly_tsp_contribution=0,
    matching_contribution=True, include_medicare=True, fehb_growth_rate=0.05,
    tsp_fund_allocation=None, use_fund_allocation=False, parameter_ranges=None
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
        pa_resident, fehb_premium, filing_status, 
        bi_weekly_tsp_contribution=bi_weekly_tsp_contribution,
        matching_contribution=matching_contribution,
        include_medicare=include_medicare,
        fehb_growth_rate=fehb_growth_rate,
        tsp_fund_allocation=tsp_fund_allocation,
        use_fund_allocation=use_fund_allocation
    )
    
    results["base_case"] = base_case
    
    # Test COLA variations
    for cola in parameter_ranges["cola"]:
        sim_df = simulate_retirement(
            birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
            ss_start_age, survivor_option, cola, tsp_growth_mean, tsp_withdraw,
            pa_resident, fehb_premium, filing_status,
            bi_weekly_tsp_contribution=bi_weekly_tsp_contribution,
            matching_contribution=matching_contribution,
            include_medicare=include_medicare,
            fehb_growth_rate=fehb_growth_rate,
            tsp_fund_allocation=tsp_fund_allocation,
            use_fund_allocation=use_fund_allocation
        )
        results["cola"][cola] = sim_df
    
    # Test TSP growth variations
    for growth in parameter_ranges["tsp_growth"]:
        sim_df = simulate_retirement(
            birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
            ss_start_age, survivor_option, cola_mean, growth, tsp_withdraw,
            pa_resident, fehb_premium, filing_status,
            bi_weekly_tsp_contribution=bi_weekly_tsp_contribution,
            matching_contribution=matching_contribution,
            include_medicare=include_medicare,
            fehb_growth_rate=fehb_growth_rate,
            tsp_fund_allocation=tsp_fund_allocation,
            use_fund_allocation=use_fund_allocation
        )
        results["tsp_growth"][growth] = sim_df
    
    # Test TSP withdrawal rate variations
    for withdraw in parameter_ranges["tsp_withdraw"]:
        sim_df = simulate_retirement(
            birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
            ss_start_age, survivor_option, cola_mean, tsp_growth_mean, withdraw,
            pa_resident, fehb_premium, filing_status,
            bi_weekly_tsp_contribution=bi_weekly_tsp_contribution,
            matching_contribution=matching_contribution,
            include_medicare=include_medicare,
            fehb_growth_rate=fehb_growth_rate,
            tsp_fund_allocation=tsp_fund_allocation,
            use_fund_allocation=use_fund_allocation
        )
        results["tsp_withdraw"][withdraw] = sim_df
    
    # Test retirement date variations
    for years in parameter_ranges["retire_delay_years"]:
        delayed_retire_date = retire_date + relativedelta(years=years)
        sim_df = simulate_retirement(
            birthdate, start_date, delayed_retire_date, high3, tsp_start, sick_leave_hours,
            ss_start_age, survivor_option, cola_mean, tsp_growth_mean, tsp_withdraw,
            pa_resident, fehb_premium, filing_status,
            bi_weekly_tsp_contribution=bi_weekly_tsp_contribution,
            matching_contribution=matching_contribution,
            include_medicare=include_medicare,
            fehb_growth_rate=fehb_growth_rate,
            tsp_fund_allocation=tsp_fund_allocation,
            use_fund_allocation=use_fund_allocation
        )
        results["retire_delay_years"][years] = sim_df
    
    return results
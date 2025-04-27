"""
retirement_model.py
------------------
Core logic for federal retirement simulation, including calculation helpers, input validation, and simulation orchestration.
"""

import datetime as dt
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
from analysis_utils import calculate_rmd

def calculate_age(birthdate, target_date):
    """Calculate age at a specific date"""
    age = target_date.year - birthdate.year - ((target_date.month, target_date.day) < (birthdate.month, birthdate.day))
    return age

def calculate_service_years(start_date, end_date, sick_leave_months=0):
    """Calculate years of service including sick leave credit"""
    service_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month
    service_years = service_months / 12
    # Add sick leave credit
    service_years += sick_leave_months / 12
    return service_years

def calculate_federal_tax(income, filing_status="single"):
    """Calculate federal tax using progressive tax brackets (2024)"""
    if filing_status == "single":
        brackets = [
            (0, 11600, 0.10),
            (11600, 47150, 0.12),
            (47150, 100525, 0.22),
            (100525, 191950, 0.24),
            (191950, 243725, 0.32),
            (243725, 609350, 0.35),
            (609350, float('inf'), 0.37)
        ]
    elif filing_status == "married":
        brackets = [
            (0, 23200, 0.10),
            (23200, 94300, 0.12),
            (94300, 201050, 0.22),
            (201050, 383900, 0.24),
            (383900, 487450, 0.32),
            (487450, 731200, 0.35),
            (731200, float('inf'), 0.37)
        ]
    
    tax = 0
    for min_income, max_income, rate in brackets:
        if income > min_income:
            taxable_in_bracket = min(income, max_income) - min_income
            tax += taxable_in_bracket * rate
    
    return tax

def get_social_security_benefit(birthdate, ss_start_age, base_benefit=None):
    """Get Social Security benefit based on start age"""
    # Default values based on your statement
    ss_benefits_by_age = {
        62: 2795,
        63: 2985,
        64: 3191,
        65: 3464,
        66: 3738,
        67: 4012,
        68: 4314,
        69: 4643,
        70: 5000
    }
    
    # Use base_benefit if provided, otherwise use the table
    if base_benefit is not None:
        # Adjust the benefit based on age
        full_retirement_age = 67  # For those born after 1960
        if ss_start_age < full_retirement_age:
            # Reduction: 5/9% for first 36 months + 5/12% for additional months
            months_early = (full_retirement_age - ss_start_age) * 12
            if months_early <= 36:
                reduction = months_early * (5/9) / 100
            else:
                reduction = 36 * (5/9) / 100 + (months_early - 36) * (5/12) / 100
            return base_benefit * (1 - reduction)
        elif ss_start_age > full_retirement_age:
            # Increase: 8% per year
            years_delayed = ss_start_age - full_retirement_age
            return base_benefit * (1 + years_delayed * 0.08)
        else:
            return base_benefit
    else:
        # Use the lookup table
        return ss_benefits_by_age.get(ss_start_age, 4012)  # Default to age 67 benefit

def calculate_fers_supplement(service_years, ss_benefit_age_62):
    """Calculate FERS supplement for retirees under age 62"""
    # For each year of service, you get 1/40th of age 62 SS benefit
    service_factor = min(service_years, 40) / 40
    return ss_benefit_age_62 * service_factor

def calculate_monthly_rmd(age, balance):
    """Calculate Required Minimum Distribution based on age"""
    if age < 73:
        return 0
    
    # Simplified life expectancy table (IRS Uniform Lifetime Table 2022+)
    life_expectancy = {
        73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9, 78: 22.0,
        79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5, 83: 17.7, 84: 16.8,
        85: 16.0, 86: 15.2, 87: 14.4, 88: 13.7, 89: 12.9, 90: 12.2,
        91: 11.5, 92: 10.8, 93: 10.1, 94: 9.5, 95: 8.9, 96: 8.4,
        97: 7.8, 98: 7.3, 99: 6.8, 100: 6.4, 101: 6.0, 102: 5.6,
        103: 5.2, 104: 4.9, 105: 4.6, 106: 4.3, 107: 4.1, 108: 3.9,
        109: 3.7, 110: 3.5, 111: 3.4, 112: 3.3, 113: 3.1, 114: 3.0,
        115: 2.9, 116: 2.8, 117: 2.7, 118: 2.5, 119: 2.3, 120: 2.0
    }
    
    # Get life expectancy factor (default to 15 if age > 120)
    factor = life_expectancy.get(age, 15.0)
    
    # Calculate annual RMD
    annual_rmd = balance / factor
    
    # Return monthly RMD
    return annual_rmd / 12

def calculate_state_tax(pa_resident, income):
    """Return state tax based on residency; extendable for other states."""
    if pa_resident:
        return 0.0
    # Default flat 3% for non-PA; customize as needed
    return income * 0.03

# Medicare premium constants (2024 rates)
MEDICARE_PART_B_PREMIUM = 174.70  # Standard monthly premium
MEDICARE_PART_D_PREMIUM = 35.00   # Average monthly premium

# Historical average TSP fund returns
TSP_FUND_RETURNS = {
    "G": 0.025,  # Very stable, low risk
    "F": 0.035,  # Fixed income, medium-low risk
    "C": 0.07,   # Tracks S&P 500, medium-high risk
    "S": 0.08,   # Small cap index, high risk
    "I": 0.065   # International stocks, high risk
}

def calculate_weighted_tsp_growth(fund_allocation):
    """Calculate weighted TSP growth rate based on fund allocation"""
    if not fund_allocation:
        return None
    
    weighted_growth = (
        fund_allocation.get("g_fund_pct", 0)/100 * TSP_FUND_RETURNS["G"] + 
        fund_allocation.get("f_fund_pct", 0)/100 * TSP_FUND_RETURNS["F"] + 
        fund_allocation.get("c_fund_pct", 0)/100 * TSP_FUND_RETURNS["C"] + 
        fund_allocation.get("s_fund_pct", 0)/100 * TSP_FUND_RETURNS["S"] + 
        fund_allocation.get("i_fund_pct", 0)/100 * TSP_FUND_RETURNS["I"]
    )
    
    return weighted_growth

# --- Helper Functions for Modularity & Validation ---
def validate_inputs(birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours, ss_start_age, cola, tsp_growth, tsp_withdraw, fehb_premium, sim_years):
    """Validate key user inputs for the simulation. Returns error list."""
    errors = []
    if not isinstance(high3, (int, float)) or high3 < 0:
        errors.append("High-3 salary cannot be negative.")
    if not isinstance(tsp_start, (int, float)) or tsp_start < 0:
        errors.append("Starting TSP balance cannot be negative.")
    if not isinstance(sick_leave_hours, (int, float)) or sick_leave_hours < 0:
        errors.append("Sick leave hours cannot be negative.")
    if not isinstance(ss_start_age, int) or ss_start_age < 62 or ss_start_age > 70:
        errors.append("Social Security start age should be between 62 and 70.")
    import numpy as np
    def is_negative(val):
        if isinstance(val, (int, float)):
            return val < 0
        arr = np.array(val)
        return np.any(arr < 0)
    if is_negative(cola):
        errors.append("COLA cannot be negative.")
    if is_negative(tsp_growth):
        errors.append("TSP growth cannot be negative.")
    if not isinstance(tsp_withdraw, (int, float)) or tsp_withdraw < 0:
        errors.append("TSP withdrawal rate cannot be negative.")
    if not isinstance(fehb_premium, (int, float)) or fehb_premium < 0:
        errors.append("FEHB premium cannot be negative.")
    if not isinstance(sim_years, int) or sim_years < 1:
        errors.append("Simulation years must be at least 1.")
    if not (isinstance(retire_date, dt.date) and isinstance(start_date, dt.date) and isinstance(birthdate, dt.date)):
        errors.append("Dates must be valid date objects.")
    elif retire_date <= start_date:
        errors.append("Retirement date must be after service start date.")
    elif birthdate >= retire_date:
        errors.append("Birthdate must be before retirement date.")
    # Warn if service years or sick leave conversion is excessive
    if sick_leave_hours > 5000:
        errors.append("Warning: Unusually high sick leave hours; please verify input.")
    return errors

def calculate_tsp_matching(bi_weekly_salary, bi_weekly_tsp_contribution, matching_contribution):
    """Calculate TSP matching amount per pay period."""
    matching_amount = 0
    if not matching_contribution or bi_weekly_salary <= 0:
        return matching_amount
    contribution_percentage = (bi_weekly_tsp_contribution / bi_weekly_salary) * 100
    # Automatic 1%
    matching_amount += bi_weekly_salary * 0.01
    # Match dollar-for-dollar on first 3%
    if contribution_percentage >= 3:
        matching_amount += bi_weekly_salary * 0.03
    else:
        matching_amount += bi_weekly_salary * (contribution_percentage / 100)
    # Match 50 cents on the dollar for next 2%
    if contribution_percentage >= 5:
        matching_amount += bi_weekly_salary * 0.01  # 50% of 2%
    elif contribution_percentage > 3:
        matching_amount += bi_weekly_salary * (contribution_percentage - 3) / 100 * 0.5
    return matching_amount

def apply_cola(base, cola, years):
    """Apply COLA to a base value for a number of years (compounded annually)."""
    return base * ((1 + cola) ** int(years))

def prorate_monthly_values(working_days, retired_days, days_in_month, working_salary, orig_f, orig_fs, orig_t, orig_ss_amt, orig_fehb_amt, orig_medicare_amt):
    """Blend working and retired values for a partial retirement month."""
    working_ratio = working_days / days_in_month
    retired_ratio = retired_days / days_in_month
    s = working_salary * working_ratio
    f = orig_f * retired_ratio
    fs = orig_fs * retired_ratio
    t = orig_t * retired_ratio
    ss_amt = orig_ss_amt * retired_ratio
    fehb_amt = orig_fehb_amt * retired_ratio
    medicare_amt = orig_medicare_amt * retired_ratio
    return s, f, fs, t, ss_amt, fehb_amt, medicare_amt

# --- Main Simulation Function ---
def simulate_retirement(birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
                       ss_start_age, survivor_option, cola, tsp_growth, tsp_withdraw, 
                       withdrawal_strategy="Greater of Both", # NEW ARGUMENT
                       pa_resident=None, fehb_premium=None, filing_status="single", sim_years=25,
                       bi_weekly_tsp_contribution=0, matching_contribution=True, include_medicare=True,
                       fehb_growth_rate=0.05, tsp_fund_allocation=None, use_fund_allocation=False,
                       current_salary=None):
    """
    Simulate retirement income streams on a monthly basis.
    Returns a DataFrame with results.
    Raises ValueError if input validation fails.
    """
    # --- Input Validation ---
    errors = validate_inputs(birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours, ss_start_age, cola, tsp_growth, tsp_withdraw, fehb_premium, sim_years)
    if errors:
        # For Streamlit: surface warnings in UI if possible
        raise ValueError("; ".join(errors))
    
    # If using fund allocation, calculate the weighted growth rate
    if use_fund_allocation and tsp_fund_allocation:
        calculated_tsp_growth = calculate_weighted_tsp_growth(tsp_fund_allocation)
        if calculated_tsp_growth is not None:
            tsp_growth = calculated_tsp_growth
    
    # Use high3 as current salary if not provided
    if current_salary is None:
        current_salary = high3
    
    # Initialize data structures
    months = []
    fers = []
    fers_supplement = []
    tsp = []
    ss = []
    salary = []
    fehb = []
    medicare = []
    total = []
    tsp_balance_history = []
    rmd_amounts = []
    
    # Convert sick leave hours to months for service credit
    sick_leave_months = sick_leave_hours / 174  # 174 hours = 1 month of service credit
    
    # Calculate service years
    service_years = calculate_service_years(start_date, retire_date, sick_leave_months)
    
    # Key dates
    today = dt.date.today()
    age_62 = birthdate + relativedelta(years=62)
    ss_start_date = birthdate + relativedelta(years=ss_start_age)
    age_65 = birthdate + relativedelta(years=65)
    
    # Determine multiplier (1.1% if retiring at/after 62 with 20+ years, otherwise 1.0%)
    qualified_for_bonus = retire_date >= age_62 and service_years >= 20
    multiplier = 0.011 if qualified_for_bonus else 0.01
    
    # Survivor benefit reduction
    survivor_reduction = {"None": 0.0, "Partial": 0.05, "Full": 0.10}[survivor_option]
    
    # Calculate gross annuity
    gross_annuity = multiplier * service_years * high3 * (1 - survivor_reduction)
    
    # Tax rates
    state_tax = calculate_state_tax(pa_resident, high3)
    
    # TSP setup
    tsp_balance = tsp_start
    
    # Social Security setup
    ss_benefit_age_62 = get_social_security_benefit(birthdate, 62)
    ss_benefit = get_social_security_benefit(birthdate, ss_start_age)
    
    # Start simulation at beginning of year of simulation
    start_year = min(today.year, retire_date.year)
    sim_start = dt.date(start_year, 1, 1)
    
    # Calculate month of retirement for partial year handling
    retirement_month = retire_date.month
    
    # Calculate simulation end date (sim_years after retirement)
    sim_end_date = retire_date + relativedelta(years=sim_years)
    
    # Run simulation from start to end date (monthly)
    date = sim_start
    # --- Handle COLA and TSP growth as arrays or scalars ---
    import numpy as np
    cola_is_array = isinstance(cola, (list, np.ndarray))
    tsp_growth_is_array = isinstance(tsp_growth, (list, np.ndarray))
    month_idx = 0

    while date <= sim_end_date:
        # Select cola and tsp_growth for this month
        # Use last value if index exceeds array length
        if cola_is_array:
            cola_this_month = cola[month_idx] if month_idx < len(cola) else cola[-1]
        else:
            cola_this_month = cola
        if tsp_growth_is_array:
            tsp_growth_this_month = tsp_growth[month_idx] if month_idx < len(tsp_growth) else tsp_growth[-1]
        else:
            tsp_growth_this_month = tsp_growth

        # Skip past dates if we're simulating from current year
        if date < today and sim_start.year == today.year:
            date += relativedelta(months=1)
            if cola_is_array or tsp_growth_is_array:
                month_idx += 1
            continue
            
        # Calculate current age for RMD purposes
        current_age = calculate_age(birthdate, date)
        
        # Debug: Add this check specifically for September 2025
        is_post_retirement = date >= retire_date
            
        # Monthly values based on current date
        if not is_post_retirement:
            # Still working
            monthly_gross_salary = high3 / 12
            # Progressive tax on salary
            annual_salary = high3
            federal_tax = calculate_federal_tax(annual_salary, filing_status) / 12
            effective_fed_rate = federal_tax / (monthly_gross_salary)
            
            s = monthly_gross_salary * (1 - effective_fed_rate - state_tax)
            f = 0
            fs = 0
            t = 0
            ss_amt = 0
            fehb_amt = 0
            medicare_amt = 0
            
            # TSP contribution and growth during working years
            if bi_weekly_tsp_contribution > 0:
                # Calculate monthly TSP contribution (26 pay periods per year / 12 months)
                bi_weekly_salary = current_salary / 26
                
                # Calculate accurate matching based on TSP rules if enabled
                matching_amount = calculate_tsp_matching(bi_weekly_salary, bi_weekly_tsp_contribution, matching_contribution)
                
                # Convert biweekly contribution to monthly (26 pay periods / 12 months)
                total_biweekly = bi_weekly_tsp_contribution + matching_amount
                monthly_contribution = total_biweekly * 26 / 12
                
                # Apply to TSP balance
                tsp_balance = tsp_balance * (1 + tsp_growth_this_month / 12) + monthly_contribution
            else:
                # No contributions, just growth
                tsp_balance = tsp_balance * (1 + tsp_growth_this_month / 12)
            
            # Initialize rmd_amount to 0 during working years
            rmd_amount = 0
            
        else:
            # Retired
            s = 0
            
            # FERS annuity with COLA
            years_retired = (date.year - retire_date.year) + (date.month - retire_date.month) / 12
            monthly_annuity = apply_cola(gross_annuity / 12, cola_this_month, years_retired)
            
            # Progressive tax on annuity
            annual_annuity = monthly_annuity * 12
            federal_tax = calculate_federal_tax(annual_annuity, filing_status) / 12
            effective_fed_rate = federal_tax / monthly_annuity if monthly_annuity > 0 else 0
            
            f = monthly_annuity * (1 - effective_fed_rate)
            
            # FERS Supplement (if under 62)
            if date < age_62 and retire_date.year - start_date.year >= 20:
                fs = calculate_fers_supplement(service_years, ss_benefit_age_62) * (1 - effective_fed_rate)
            else:
                fs = 0
            
            # Check for RMD requirements
            rmd_amount = calculate_rmd(current_age, tsp_balance)
            # --- Withdrawal strategy logic ---
            if withdrawal_strategy == "Fixed Percentage":
                withdrawal_rate = tsp_withdraw / 12
            elif withdrawal_strategy == "IRS RMD":
                withdrawal_rate = (rmd_amount / tsp_balance) if tsp_balance > 0 else 0
            else: # "Greater of Both"
                withdrawal_rate = max(tsp_withdraw / 12, rmd_amount / tsp_balance if tsp_balance > 0 else 0)
            
            # TSP withdrawals and growth
            tsp_draw = tsp_balance * withdrawal_rate if tsp_balance > 0 else 0
            
            # Progressive tax on TSP
            annual_tsp = tsp_draw * 12
            tsp_federal_tax = calculate_federal_tax(annual_tsp, filing_status) / 12
            effective_tsp_rate = tsp_federal_tax / tsp_draw if tsp_draw > 0 else 0
            
            t = tsp_draw * (1 - effective_tsp_rate)
            tsp_balance = (tsp_balance - tsp_draw) * (1 + tsp_growth_this_month / 12)
            
            # Prevent negative TSP balance
            if tsp_balance < 0:
                tsp_balance = 0
            
            # Social Security
            if date >= ss_start_date:
                years_on_ss = (date.year - ss_start_date.year) + (date.month - ss_start_date.month) / 12
                monthly_ss = apply_cola(ss_benefit, cola_this_month, years_on_ss)
                
                # 85% of SS may be taxable depending on income
                # Simplified calculation
                total_monthly_income = monthly_annuity + tsp_draw + monthly_ss
                if total_monthly_income > 5000:  # Approx threshold
                    ss_taxable_portion = 0.85
                elif total_monthly_income > 3000:
                    ss_taxable_portion = 0.50
                else:
                    ss_taxable_portion = 0
                
                ss_taxable = monthly_ss * ss_taxable_portion
                ss_tax = ss_taxable * effective_fed_rate
                
                ss_amt = monthly_ss - ss_tax
            else:
                ss_amt = 0
            
            # Prevent negative Social Security
            if ss_amt < 0:
                ss_amt = 0
            
            # FEHB premium in retirement with growth over time
            years_in_retirement = (date.year - retire_date.year) + (date.month - retire_date.month) / 12
            fehb_growth_factor = (1 + fehb_growth_rate) ** int(years_in_retirement)
            current_fehb_premium = fehb_premium * fehb_growth_factor
            fehb_amt = -current_fehb_premium
            
            # Medicare premiums at age 65+
            if include_medicare and current_age >= 65:
                medicare_amt = -(MEDICARE_PART_B_PREMIUM + MEDICARE_PART_D_PREMIUM)
            else:
                medicare_amt = 0
        
        # Robust proration for the retirement month
        import calendar
        if date.year == retire_date.year and date.month == retire_date.month:
            days_in_month = calendar.monthrange(date.year, date.month)[1]
            working_days = retire_date.day - 1
            retired_days = days_in_month - working_days
            working_ratio = working_days / days_in_month
            retired_ratio = retired_days / days_in_month

            # Calculate working portion
            monthly_gross_salary = high3 / 12
            annual_salary = high3
            federal_tax = calculate_federal_tax(annual_salary, filing_status) / 12
            effective_fed_rate = federal_tax / monthly_gross_salary
            salary_working = monthly_gross_salary * (1 - effective_fed_rate - state_tax)

            # Calculate retired portion
            years_retired = 0  # Just started
            monthly_annuity = apply_cola(gross_annuity / 12, cola_this_month, years_retired)
            annual_annuity = monthly_annuity * 12
            federal_tax_ann = calculate_federal_tax(annual_annuity, filing_status) / 12
            effective_fed_rate_ann = federal_tax_ann / monthly_annuity if monthly_annuity > 0 else 0
            fers_retired = monthly_annuity * (1 - effective_fed_rate_ann)

            # FERS Supplement (if under 62)
            if date < age_62 and service_years >= 20:
                fers_supp_retired = calculate_fers_supplement(service_years, ss_benefit_age_62) * (1 - effective_fed_rate_ann)
            else:
                fers_supp_retired = 0

            # TSP withdrawal (use standard logic for retired portion)
            rmd_amount = calculate_rmd(calculate_age(birthdate, date), tsp_balance)
            if withdrawal_strategy == "Fixed Percentage":
                withdrawal_rate = tsp_withdraw / 12
            elif withdrawal_strategy == "IRS RMD":
                withdrawal_rate = (rmd_amount / tsp_balance) if tsp_balance > 0 else 0
            else: # "Greater of Both"
                withdrawal_rate = max(tsp_withdraw / 12, rmd_amount / tsp_balance if tsp_balance > 0 else 0)
            tsp_draw_retired = tsp_balance * withdrawal_rate if tsp_balance > 0 else 0
            annual_tsp = tsp_draw_retired * 12
            tsp_federal_tax = calculate_federal_tax(annual_tsp, filing_status) / 12
            effective_tsp_rate = tsp_federal_tax / tsp_draw_retired if tsp_draw_retired > 0 else 0
            tsp_retired = tsp_draw_retired * (1 - effective_tsp_rate)

            # Social Security (if eligible)
            if date >= ss_start_date:
                years_on_ss = (date.year - ss_start_date.year) + (date.month - ss_start_date.month) / 12
                monthly_ss = apply_cola(ss_benefit, cola_this_month, years_on_ss)
                total_monthly_income = monthly_annuity + tsp_draw_retired + monthly_ss
                if total_monthly_income > 5000:
                    ss_taxable_portion = 0.85
                elif total_monthly_income > 3000:
                    ss_taxable_portion = 0.50
                else:
                    ss_taxable_portion = 0
                ss_taxable = monthly_ss * ss_taxable_portion
                ss_tax = ss_taxable * effective_fed_rate_ann
                ss_amt_retired = monthly_ss - ss_tax
            else:
                ss_amt_retired = 0

            # FEHB and Medicare (retired portion)
            years_in_retirement = 0
            fehb_growth_factor = (1 + fehb_growth_rate) ** int(years_in_retirement)
            current_fehb_premium = fehb_premium * fehb_growth_factor
            fehb_amt_retired = -current_fehb_premium
            medicare_amt_retired = -(MEDICARE_PART_B_PREMIUM + MEDICARE_PART_D_PREMIUM) if include_medicare and calculate_age(birthdate, date) >= 65 else 0

            # Prorate all values
            s = salary_working * working_ratio
            f = fers_retired * retired_ratio
            fs = fers_supp_retired * retired_ratio
            t = tsp_retired * retired_ratio
            ss_amt = ss_amt_retired * retired_ratio
            fehb_amt = fehb_amt_retired * retired_ratio
            medicare_amt = medicare_amt_retired * retired_ratio
        
        # Record data
        
        # Debug fix for the September 2025 issue: ensure salary is zero for months after retirement
        if date > retire_date:
            s = 0
        
        months.append(date)
        fers.append(f)
        fers_supplement.append(fs)
        tsp.append(t)
        ss.append(ss_amt)
        salary.append(s)
        fehb.append(fehb_amt)
        medicare.append(medicare_amt)
        total.append(f + fs + t + ss_amt + s + fehb_amt + medicare_amt)
        tsp_balance_history.append(tsp_balance)
        rmd_amounts.append(rmd_amount)
        
        # Advance to next month
        date += relativedelta(months=1)
        if cola_is_array or tsp_growth_is_array:
            month_idx += 1
    
    # Create DataFrame
    df = pd.DataFrame({
        "Date": months,
        "Salary": salary,
        "FERS": fers,
        "FERS_Supplement": fers_supplement,
        "TSP": tsp,
        "Social_Security": ss,
        "FEHB": fehb,
        "Medicare": medicare,
        "Total_Income": total,
        "TSP_Balance": tsp_balance_history,
        "RMD_Amount": rmd_amounts
    })
    
    # Special fix for the September 2025 spike issue
    # Find any row where salary is abnormally high (over annual salary / 2)
    abnormal_salary_mask = df["Salary"] > (high3 / 2)
    # Also ensure we're only fixing dates after retirement
    post_retirement_mask = df["Date"] > retire_date
    # Apply both conditions to identify problematic rows
    fix_mask = abnormal_salary_mask & post_retirement_mask
    
    if fix_mask.any():
        # Fix the problematic rows by setting salary to 0 and recalculating total income
        df.loc[fix_mask, "Salary"] = 0
        # Recalculate total income for these rows
        df.loc[fix_mask, "Total_Income"] = (
            df.loc[fix_mask, "FERS"] + 
            df.loc[fix_mask, "FERS_Supplement"] + 
            df.loc[fix_mask, "TSP"] + 
            df.loc[fix_mask, "Social_Security"] + 
            df.loc[fix_mask, "FEHB"] +
            df.loc[fix_mask, "Medicare"]
        )
    
    return df

# --- Unit Test for Tax Calculation ---
def _test_calculate_federal_tax():
    # 2024 single filer: 50,000 should be taxed as:
    # 0-11,600 @10%, 11,600-47,150 @12%, 47,150-50,000 @22%
    expected = (11600-0)*0.10 + (47150-11600)*0.12 + (50000-47150)*0.22
    actual = calculate_federal_tax(50000, "single")
    assert abs(actual - expected) < 1e-2, f"Expected {expected}, got {actual}"

# --- Additional Unit Test for Simulation ---
def _test_simulate_retirement_basic():
    """Basic test: Simulation returns non-empty DataFrame and no negative balances."""
    import datetime as dt
    birthdate = dt.date(1960, 1, 1)
    start_date = dt.date(1985, 1, 1)
    retire_date = dt.date(2025, 1, 1)
    df = simulate_retirement(
        birthdate, start_date, retire_date, high3=100000, tsp_start=50000, sick_leave_hours=0,
        ss_start_age=67, survivor_option="None", cola=0.02, tsp_growth=0.05, tsp_withdraw=0.04,
        pa_resident=True, fehb_premium=200, filing_status="single", sim_years=5
    )
    assert not df.empty, "Simulation output should not be empty."
    assert (df["TSP_Balance"] >= 0).all(), "TSP balance should never be negative."
    assert (df["Social_Security"] >= 0).all(), "Social Security should never be negative."

if __name__ == "__main__":
    _test_calculate_federal_tax()
    _test_simulate_retirement_basic()
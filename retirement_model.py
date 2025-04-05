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

def simulate_retirement(birthdate, start_date, retire_date, high3, tsp_start, sick_leave_hours,
                        ss_start_age, survivor_option, cola, tsp_growth, tsp_withdraw, 
                        pa_resident, fehb_premium, filing_status="single"):
    """
    Simulate retirement income streams on a monthly basis
    """
    # Initialize data structures
    months = []
    fers = []
    fers_supplement = []
    tsp = []
    ss = []
    salary = []
    fehb = []
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
    
    # Determine multiplier (1.1% if retiring at/after 62 with 20+ years, otherwise 1.0%)
    qualified_for_bonus = retire_date >= age_62 and service_years >= 20
    multiplier = 0.011 if qualified_for_bonus else 0.01
    
    # Survivor benefit reduction
    survivor_reduction = {"None": 0.0, "Partial": 0.05, "Full": 0.10}[survivor_option]
    
    # Calculate gross annuity
    gross_annuity = multiplier * service_years * high3 * (1 - survivor_reduction)
    
    # Tax rates
    state_tax = 0.03 if not pa_resident else 0.00
    
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
    
    # Run simulation for 40 years (monthly)
    date = sim_start
    for _ in range(40 * 12):
        # Skip past dates if we're simulating from current year
        if date < today and sim_start.year == today.year:
            date += relativedelta(months=1)
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
            
            # TSP contribution and growth during working years
            # Assuming no withdrawals and continued growth
            tsp_balance = tsp_balance * (1 + tsp_growth / 12)
            
            # Initialize rmd_amount to 0 during working years
            rmd_amount = 0
            
        else:
            # Retired
            s = 0
            
            # FERS annuity with COLA
            years_retired = (date.year - retire_date.year) + (date.month - retire_date.month) / 12
            cola_applied = (1 + cola) ** int(years_retired)
            monthly_annuity = (gross_annuity / 12) * cola_applied
            
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
            withdrawal_rate = max(tsp_withdraw / 12, rmd_amount / tsp_balance if tsp_balance > 0 else 0)
            
            # TSP withdrawals and growth
            tsp_draw = tsp_balance * withdrawal_rate if tsp_balance > 0 else 0
            
            # Progressive tax on TSP
            annual_tsp = tsp_draw * 12
            tsp_federal_tax = calculate_federal_tax(annual_tsp, filing_status) / 12
            effective_tsp_rate = tsp_federal_tax / tsp_draw if tsp_draw > 0 else 0
            
            t = tsp_draw * (1 - effective_tsp_rate)
            tsp_balance = (tsp_balance - tsp_draw) * (1 + tsp_growth / 12)
            
            # Social Security
            if date >= ss_start_date:
                years_on_ss = (date.year - ss_start_date.year) + (date.month - ss_start_date.month) / 12
                ss_cola_applied = (1 + cola) ** int(years_on_ss)
                monthly_ss = ss_benefit * ss_cola_applied
                
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
                
            # FEHB premium in retirement
            fehb_amt = -fehb_premium
        
        # Special handling for mid-year retirement
        if date.year == retire_date.year:
            if date.month == retirement_month:
                # Retirement month - prorate based on day of month
                days_in_month = (dt.date(date.year, date.month, 28) + relativedelta(days=4)).day
                working_days = retire_date.day - 1
                retired_days = days_in_month - working_days
                
                # Blend working and retired values
                working_ratio = working_days / days_in_month
                retired_ratio = retired_days / days_in_month
                
                # Calculate working part of month
                monthly_gross_salary = high3 / 12
                annual_salary = high3
                federal_tax = calculate_federal_tax(annual_salary, filing_status) / 12
                effective_fed_rate = federal_tax / monthly_gross_salary
                working_salary = monthly_gross_salary * (1 - effective_fed_rate - state_tax) * working_ratio
                
                # Store original values for retirement portion calculations
                orig_f = f
                orig_fs = fs
                orig_t = t
                orig_ss_amt = ss_amt
                orig_fehb_amt = fehb_amt
                
                # Reset all values to avoid double-counting
                s = 0
                f = 0
                fs = 0
                t = 0
                ss_amt = 0
                fehb_amt = 0
                
                # Adjust values for partial month - only count each portion once
                s = working_salary  # Salary for working days only
                f = orig_f * retired_ratio  # Retirement benefits only for retired days
                fs = orig_fs * retired_ratio
                t = orig_t * retired_ratio
                ss_amt = orig_ss_amt * retired_ratio
                fehb_amt = orig_fehb_amt * retired_ratio
        
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
        total.append(f + fs + t + ss_amt + s + fehb_amt)
        tsp_balance_history.append(tsp_balance)
        rmd_amounts.append(rmd_amount)
        
        # Advance to next month
        date += relativedelta(months=1)
    
    # Create DataFrame
    df = pd.DataFrame({
        "Date": months,
        "Salary": salary,
        "FERS": fers,
        "FERS_Supplement": fers_supplement,
        "TSP": tsp,
        "Social_Security": ss,
        "FEHB": fehb,
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
            df.loc[fix_mask, "FEHB"]
        )
    
    return df
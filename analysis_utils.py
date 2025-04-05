"""
Utility functions for analyzing retirement scenarios.
This module centralizes calculation logic used across different parts of the application.
"""

import pandas as pd
from dateutil.relativedelta import relativedelta

def calculate_cumulative_income(df):
    """Calculate and add cumulative income to a dataframe"""
    df["Cumulative_Income"] = df["Total_Income"].cumsum()
    return df

def find_breakeven_point(df_a, df_b):
    """Find breakeven point between two scenarios"""
    delta_cum = df_b["Cumulative_Income"] - df_a["Cumulative_Income"]
    breakeven_idx = None
    breakeven_date = None
    breakeven_value = None
    
    if (delta_cum <= 0).any() and (delta_cum >= 0).any():
        # There is a crossover point
        for i in range(1, len(delta_cum)):
            if (delta_cum.iloc[i-1] <= 0 and delta_cum.iloc[i] > 0) or \
               (delta_cum.iloc[i-1] >= 0 and delta_cum.iloc[i] < 0):
                breakeven_idx = i
                break
        
        if breakeven_idx:
            breakeven_date = df_a["Date"].iloc[breakeven_idx]
            breakeven_value = df_a["Cumulative_Income"].iloc[breakeven_idx]
    
    return breakeven_idx, breakeven_date, breakeven_value

def create_combined_household_data(df_a, df_b):
    """Create combined household data from two scenarios"""
    combined_sources = pd.DataFrame({
        "Date": df_a["Date"],
        "Salary": df_a["Salary"] + df_b["Salary"],
        "FERS": df_a["FERS"] + df_b["FERS"],
        "FERS_Supplement": df_a["FERS_Supplement"] + df_b["FERS_Supplement"],
        "TSP": df_a["TSP"] + df_b["TSP"],
        "Social_Security": df_a["Social_Security"] + df_b["Social_Security"],
        "FEHB": df_a["FEHB"] + df_b["FEHB"],
        "Total_Income": df_a["Total_Income"] + df_b["Total_Income"]
    })
    
    combined_sources["Cumulative_Income"] = combined_sources["Total_Income"].cumsum()
    
    return combined_sources

def calculate_expenses(dates, retire_date, pre_retire_expenses, post_retire_expenses, inflation_rate):
    """Calculate monthly expenses with inflation adjustment"""
    expenses = []
    
    start_year = dates[0].year
    
    for date in dates:
        # Determine base expense amount
        if date < retire_date:
            base_expense = pre_retire_expenses
        else:
            base_expense = post_retire_expenses
        
        # Apply inflation
        years_from_start = date.year - start_year + (date.month - dates[0].month) / 12
        inflation_factor = (1 + inflation_rate) ** years_from_start
        
        monthly_expense = base_expense * inflation_factor
        expenses.append(monthly_expense)
    
    return expenses

def calculate_cash_flow(df, expenses):
    """Calculate monthly and cumulative cash flow"""
    df["Monthly_Expenses"] = expenses
    df["Net_Cash_Flow"] = df["Total_Income"] - df["Monthly_Expenses"]
    df["Cumulative_Cash_Flow"] = df["Net_Cash_Flow"].cumsum()
    return df

def calculate_rmd(age, tsp_balance):
    """Calculate Required Minimum Distribution based on age and TSP balance"""
    # RMD calculation based on IRS life expectancy tables
    # This is a simplified version
    if age < 72:  # No RMD before age 72
        return 0
    
    # Approximate life expectancy factors
    life_expectancy = max(120 - age, 15)  # Simple approximation
    
    # Annual RMD amount
    annual_rmd = tsp_balance / life_expectancy
    
    # Return monthly amount
    return annual_rmd / 12
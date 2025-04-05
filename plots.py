import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.dates as mdates

def plot_income_sources(df, retire_date, ss_date, scenario_title):
    """
    Plot stacked area chart of income sources with FEHB shown separately as expense annotation
    """
    # Create figure and axis for income
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create copy of data for plotting
    plot_df = df.copy()
    
    # Get dates for x-axis
    dates = plot_df["Date"]
    
    # Plot positive income streams as a stack (excluding FEHB)
    ax.stackplot(dates,
                plot_df["Salary"],
                plot_df["FERS"],
                plot_df["FERS_Supplement"],
                plot_df["TSP"],
                plot_df["Social_Security"],
                labels=["Salary", "FERS Annuity", "FERS Supplement", "TSP", "Social Security"])
    
    # Calculate total positive income
    positive_income = (
        plot_df["Salary"] + 
        plot_df["FERS"] + 
        plot_df["FERS_Supplement"] + 
        plot_df["TSP"] + 
        plot_df["Social_Security"]
    )
    
    # Calculate net income (after FEHB)
    net_income = positive_income + plot_df["FEHB"]
    
    # Plot net income line (after FEHB expense)
    ax.plot(
        dates,
        net_income,
        color='black',
        linestyle='-',
        linewidth=2.0,
        label="Net Income after FEHB"
    )
    
    # Add small annotations for FEHB expense at regular intervals
    # This avoids the overlapping bar issue
    annotation_indices = np.linspace(0, len(dates)-1, 10, dtype=int)
    for idx in annotation_indices:
        date = dates.iloc[idx]
        fehb_value = plot_df["FEHB"].iloc[idx]
        ax.annotate(
            f"FEHB: ${abs(fehb_value):.0f}",
            xy=(date, net_income.iloc[idx]),
            xytext=(0, -20),
            textcoords="offset points",
            ha='center',
            va='top',
            color='darkred',
            fontsize=8,
            arrowprops=dict(arrowstyle='->', color='darkred', lw=1)
        )
    
    # Add retirement and SS date lines
    ax.axvline(x=retire_date, color='r', linestyle='--', label="Retirement")
    ax.axvline(x=ss_date, color='g', linestyle=':', label="Social Security")
    
    # Format plot
    ax.set_title(f"Income Source Breakdown - {scenario_title}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Monthly Income ($)")
    ax.legend(loc='upper left')
    ax.grid(True)
    
    # Set reasonable y-limits
    ax.set_ylim(0, positive_income.max() * 1.1)
    
    # Add a text note about FEHB
    avg_fehb = abs(plot_df["FEHB"].mean())
    ax.text(
        0.02, 0.02, 
        f"Note: FEHB premiums average ${avg_fehb:.0f}/month and are deducted from total income",
        transform=ax.transAxes,
        bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'),
        fontsize=9
    )
    
    # Set better date formatting
    years = mdates.YearLocator(5)   # every 5 years
    years_fmt = mdates.DateFormatter('%Y')
    ax.xaxis.set_major_locator(years)
    ax.xaxis.set_major_formatter(years_fmt)
    
    return fig

def plot_monthly_income(df_a, df_b, retire_date_a, retire_date_b, ss_date_a, ss_date_b):
    """Plot monthly income comparison between two scenarios"""
    # Add retirement date markers
    chart_data = pd.DataFrame({
        "Date": df_a["Date"],
        "Scenario A": df_a["Total_Income"],
        "Scenario B": df_b["Total_Income"]
    })
    
    # Create line chart
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(chart_data["Date"], chart_data["Scenario A"], label="Scenario A")
    ax.plot(chart_data["Date"], chart_data["Scenario B"], label="Scenario B")
    
    # Add retirement date lines
    ax.axvline(x=retire_date_a, color='r', linestyle='--', label="A Retirement")
    ax.axvline(x=retire_date_b, color='g', linestyle='--', label="B Retirement")
    
    # Add Social Security start dates
    ax.axvline(x=ss_date_a, color='r', linestyle=':', label="A Social Security")
    ax.axvline(x=ss_date_b, color='g', linestyle=':', label="B Social Security")
    
    # Format plot
    ax.set_title("Monthly Income Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Monthly Income ($)")
    ax.legend()
    ax.grid(True)
    
    return fig

def plot_monthly_delta(delta_df, retire_date_a, retire_date_b):
    """Plot monthly income delta between two scenarios"""
    # Create delta chart
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(delta_df["Date"], delta_df["Monthly_Delta"], color='purple')
    ax.axhline(y=0, color='gray', linestyle='-')
    
    # Add retirement date lines
    ax.axvline(x=retire_date_a, color='r', linestyle='--', label="A Retirement")
    ax.axvline(x=retire_date_b, color='g', linestyle='--', label="B Retirement")
    
    # Format plot
    ax.set_title("Monthly Income Difference (B - A)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Monthly Difference ($)")
    ax.legend()
    ax.grid(True)
    
    return fig

def plot_cumulative_income(df_a, df_b, retire_date_a, retire_date_b, 
                          breakeven_date=None, breakeven_value=None, breakeven_idx=None):
    """Plot cumulative income comparison with breakeven point"""
    # Create cumulative income chart
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df_a["Date"], df_a["Cumulative_Income"], label="Scenario A")
    ax.plot(df_b["Date"], df_b["Cumulative_Income"], label="Scenario B")
    
    # Add retirement date lines
    ax.axvline(x=retire_date_a, color='r', linestyle='--', label="A Retirement")
    ax.axvline(x=retire_date_b, color='g', linestyle='--', label="B Retirement")
    
    # Add breakeven point if exists
    if breakeven_date and breakeven_value and breakeven_idx is not None:
        delta_cum = df_b["Cumulative_Income"] - df_a["Cumulative_Income"]
        
        ax.scatter([breakeven_date], [breakeven_value], color='black', s=100, zorder=5)
        ax.annotate(f"Breakeven: {breakeven_date.strftime('%b %Y')}", 
                   xy=(breakeven_date, breakeven_value),
                   xytext=(30, 30),
                   textcoords="offset points",
                   arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"))
    
    # Format plot
    ax.set_title("Cumulative Income Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Income ($)")
    ax.legend()
    ax.grid(True)
    
    return fig

def plot_household_income(dates, combined_income, retire_date_a, retire_date_b, ss_date_a, ss_date_b):
    """Plot combined household monthly income"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot combined monthly income
    ax.plot(dates, combined_income, label="Combined Monthly Income", color="purple", linewidth=2)
    
    # Add retirement date lines
    ax.axvline(x=retire_date_a, color='r', linestyle='--', label="A Retirement")
    ax.axvline(x=retire_date_b, color='g', linestyle='--', label="B Retirement")
    
    # Add Social Security start dates
    ax.axvline(x=ss_date_a, color='r', linestyle=':', label="A Social Security")
    ax.axvline(x=ss_date_b, color='g', linestyle=':', label="B Social Security")
    
    # Format plot
    ax.set_title("Combined Household Monthly Income")
    ax.set_xlabel("Date")
    ax.set_ylabel("Monthly Income ($)")
    ax.legend()
    ax.grid(True)
    
    return fig

def plot_combined_sources(combined_sources, retire_date_a, retire_date_b):
    """Plot stacked area chart for combined income sources with FEHB as expense"""
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot income sources (excluding FEHB)
    ax.stackplot(combined_sources["Date"],
                combined_sources["Salary"],
                combined_sources["FERS"],
                combined_sources["FERS_Supplement"],
                combined_sources["TSP"],
                combined_sources["Social_Security"],
                labels=["Salary", "FERS Annuity", "FERS Supplement", "TSP", "Social Security"])
    
    # Calculate positive income total
    positive_income = (
        combined_sources["Salary"] + 
        combined_sources["FERS"] + 
        combined_sources["FERS_Supplement"] + 
        combined_sources["TSP"] + 
        combined_sources["Social_Security"]
    )
    
    # Calculate net income after FEHB
    net_income = positive_income + combined_sources["FEHB"]
    
    # Plot net income line
    ax.plot(
        combined_sources["Date"],
        net_income,
        color='black',
        linestyle='-',
        linewidth=2.0,
        label="Net Income after FEHB"
    )
    
    # Add FEHB expense annotations at intervals
    annotation_indices = np.linspace(0, len(combined_sources)-1, 8, dtype=int)
    for idx in annotation_indices:
        date = combined_sources["Date"].iloc[idx]
        fehb_value = combined_sources["FEHB"].iloc[idx]
        ax.annotate(
            f"FEHB: ${abs(fehb_value):.0f}",
            xy=(date, net_income.iloc[idx]),
            xytext=(0, -20),
            textcoords="offset points",
            ha='center',
            va='top',
            color='darkred',
            fontsize=8,
            arrowprops=dict(arrowstyle='->', color='darkred', lw=1)
        )
    
    # Add info about average FEHB expense
    avg_fehb = abs(combined_sources["FEHB"].mean())
    ax.text(
        0.02, 0.02, 
        f"Note: FEHB premiums average ${avg_fehb:.0f}/month and are deducted from total income",
        transform=ax.transAxes,
        bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'),
        fontsize=9
    )
    
    # Add retirement date lines
    ax.axvline(x=retire_date_a, color='r', linestyle='--', label="A Retirement")
    ax.axvline(x=retire_date_b, color='g', linestyle='--', label="B Retirement")
    
    # Format plot
    ax.set_title("Combined Household Income Sources")
    ax.set_xlabel("Date")
    ax.set_ylabel("Monthly Income ($)")
    ax.legend(loc="upper left")
    ax.grid(True)
    
    # Set reasonable y-limit for the income
    ax.set_ylim(0, positive_income.max() * 1.1)
    
    # Set better date formatting
    years = mdates.YearLocator(5)   # every 5 years
    years_fmt = mdates.DateFormatter('%Y')
    ax.xaxis.set_major_locator(years)
    ax.xaxis.set_major_formatter(years_fmt)
    
    return fig

def plot_cumulative_household(dates, combined_cumulative, retire_date_a, retire_date_b):
    """Plot cumulative household income"""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, combined_cumulative, label="Combined Cumulative Income", color="green", linewidth=2)
    
    # Add retirement date lines
    ax.axvline(x=retire_date_a, color='r', linestyle='--', label="A Retirement")
    ax.axvline(x=retire_date_b, color='g', linestyle='--', label="B Retirement")
    
    # Format plot
    ax.set_title("Combined Cumulative Household Income")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Income ($)")
    ax.legend()
    ax.grid(True)
    
    return fig

def plot_income_ratio(income_ratio, retire_date_a, retire_date_b):
    """Plot income ratio analysis"""
    # Plot income ratios
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.stackplot(income_ratio["Date"],
                income_ratio["Fixed_Income_Ratio"] * 100,
                income_ratio["Variable_Income_Ratio"] * 100,
                labels=["Fixed Income (FERS + SS)", "Variable Income (TSP)"])
    
    # Add retirement date lines
    ax.axvline(x=retire_date_a, color='r', linestyle='--', label="A Retirement")
    ax.axvline(x=retire_date_b, color='g', linestyle='--', label="B Retirement")
    
    # Format plot
    ax.set_title("Income Source Ratio")
    ax.set_xlabel("Date")
    ax.set_ylabel("Percentage of Total Income (%)")
    ax.legend(loc="upper left")
    ax.set_ylim(0, 100)
    ax.grid(True)
    
    return fig

def plot_tsp_balance(df, retire_date):
    """Plot TSP balance over time"""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["Date"], df["TSP_Balance"], label="TSP Balance", color="green")
    
    # Add retirement date line
    ax.axvline(x=retire_date, color='r', linestyle='--', label="Retirement")
    
    # Format plot
    ax.set_title("TSP Balance Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Balance ($)")
    ax.legend()
    ax.grid(True)
    
    # Set better date formatting
    years = mdates.YearLocator(5)   # every 5 years
    years_fmt = mdates.DateFormatter('%Y')
    ax.xaxis.set_major_locator(years)
    ax.xaxis.set_major_formatter(years_fmt)
    
    return fig

def plot_rmd_vs_withdrawal(df, retire_date):
    """Plot RMD vs actual withdrawal rate"""
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Calculate actual withdrawal amount
    withdrawal = df["TSP"] / (1 - 0.22)  # Approximate pre-tax withdrawal
    
    ax.plot(df["Date"], df["RMD_Amount"], label="Required Minimum Distribution", 
            color="red", linestyle="--")
    ax.plot(df["Date"], withdrawal, label="Actual Withdrawal", color="blue")
    
    # Add retirement date line
    ax.axvline(x=retire_date, color='green', linestyle='--', label="Retirement")
    
    # Format plot
    ax.set_title("RMD vs Actual TSP Withdrawal")
    ax.set_xlabel("Date")
    ax.set_ylabel("Monthly Amount ($)")
    ax.legend()
    ax.grid(True)
    
    # Set better date formatting
    years = mdates.YearLocator(5)   # every 5 years
    years_fmt = mdates.DateFormatter('%Y')
    ax.xaxis.set_major_locator(years)
    ax.xaxis.set_major_formatter(years_fmt)
    
    return fig

def plot_cash_flow(df, retire_date):
    """Plot cash flow analysis with expenses"""
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Plot income and expenses
    ax.plot(df["Date"], df["Total_Income"], label="Total Income", color="blue")
    ax.plot(df["Date"], df["Monthly_Expenses"], label="Monthly Expenses", color="red")
    ax.plot(df["Date"], df["Net_Cash_Flow"], label="Net Cash Flow", color="green")
    
    # Add retirement date line
    ax.axvline(x=retire_date, color='purple', linestyle='--', label="Retirement")
    
    # Format plot
    ax.set_title("Monthly Cash Flow Analysis")
    ax.set_xlabel("Date")
    ax.set_ylabel("Amount ($)")
    ax.legend()
    ax.grid(True)
    
    # Set better date formatting
    years = mdates.YearLocator(5)   # every 5 years
    years_fmt = mdates.DateFormatter('%Y')
    ax.xaxis.set_major_locator(years)
    ax.xaxis.set_major_formatter(years_fmt)
    
    return fig

def plot_cumulative_cash_flow(df, retire_date):
    """Plot cumulative cash flow over time"""
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Plot cumulative cash flow
    ax.plot(df["Date"], df["Cumulative_Cash_Flow"], label="Cumulative Cash Flow", color="green")
    
    # Add retirement date line
    ax.axvline(x=retire_date, color='r', linestyle='--', label="Retirement")
    
    # Format plot
    ax.set_title("Cumulative Cash Flow Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Amount ($)")
    ax.legend()
    ax.grid(True)
    
    # Set better date formatting
    years = mdates.YearLocator(5)   # every 5 years
    years_fmt = mdates.DateFormatter('%Y')
    ax.xaxis.set_major_locator(years)
    ax.xaxis.set_major_formatter(years_fmt)
    
    return fig

def plot_stress_test_comparison(results, retire_date):
    """Plot comparison of different market scenarios"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot the different scenarios
    ax.plot(
        results["best_case"]["Date"], 
        results["best_case"]["Total_Income"], 
        label="Best Case", 
        color="green"
    )
    ax.plot(
        results["average_case"]["Date"], 
        results["average_case"]["Total_Income"], 
        label="Average Case", 
        color="blue"
    )
    ax.plot(
        results["worst_case"]["Date"], 
        results["worst_case"]["Total_Income"], 
        label="Worst Case", 
        color="red"
    )
    
    # Add retirement date line
    ax.axvline(x=retire_date, color='purple', linestyle='--', label="Retirement")
    
    # Format plot
    ax.set_title("Income Under Different Market Scenarios")
    ax.set_xlabel("Date")
    ax.set_ylabel("Monthly Income ($)")
    ax.legend()
    ax.grid(True)
    
    # Set better date formatting
    years = mdates.YearLocator(5)   # every 5 years
    years_fmt = mdates.DateFormatter('%Y')
    ax.xaxis.set_major_locator(years)
    ax.xaxis.set_major_formatter(years_fmt)
    
    return fig

def plot_tsp_stress_test(results, retire_date):
    """Plot TSP balance under different market scenarios"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot the different scenarios
    ax.plot(
        results["best_case"]["Date"], 
        results["best_case"]["TSP_Balance"], 
        label="Best Case", 
        color="green"
    )
    ax.plot(
        results["average_case"]["Date"], 
        results["average_case"]["TSP_Balance"], 
        label="Average Case", 
        color="blue"
    )
    ax.plot(
        results["worst_case"]["Date"], 
        results["worst_case"]["TSP_Balance"], 
        label="Worst Case", 
        color="red"
    )
    
    # Add retirement date line
    ax.axvline(x=retire_date, color='purple', linestyle='--', label="Retirement")
    
    # Format plot
    ax.set_title("TSP Balance Under Different Market Scenarios")
    ax.set_xlabel("Date")
    ax.set_ylabel("TSP Balance ($)")
    ax.legend()
    ax.grid(True)
    
    # Set better date formatting
    years = mdates.YearLocator(5)   # every 5 years
    years_fmt = mdates.DateFormatter('%Y')
    ax.xaxis.set_major_locator(years)
    ax.xaxis.set_major_formatter(years_fmt)
    
    return fig
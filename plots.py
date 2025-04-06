import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.dates as mdates
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

# Helper function to safely convert dates for Plotly
def safe_date_for_plotly(date_obj):
    if date_obj is None:
        return None
    # Convert date to datetime before getting timestamp
    if isinstance(date_obj, datetime.date) and not isinstance(date_obj, datetime.datetime):
        # Convert to datetime at midnight
        date_obj = datetime.datetime.combine(date_obj, datetime.time.min)
    # Convert to timestamp which Plotly can handle in milliseconds
    return date_obj.timestamp() * 1000  # Convert to milliseconds

def plot_income_sources(df, retire_date, ss_date, scenario_title, use_plotly=True):
    """
    Plot stacked area chart of income sources with FEHB shown separately as expense annotation
    """
    # Create copy of data for plotting
    plot_df = df.copy()
    
    # Get dates for x-axis
    dates = plot_df["Date"]
    
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
    
    # Calculate average FEHB expense
    avg_fehb = abs(plot_df["FEHB"].mean())
    
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Add stacked area traces for income sources
        fig.add_trace(go.Scatter(
            x=dates, y=plot_df["Salary"],
            mode='none', fill='tozeroy', name="Salary",
            fillcolor='rgba(65, 105, 225, 0.7)'
        ))
        
        # Calculate cumulative sums for proper stacking
        fers_stack = plot_df["Salary"] + plot_df["FERS"]
        fig.add_trace(go.Scatter(
            x=dates, y=fers_stack,
            mode='none', fill='tonexty', name="FERS Annuity",
            fillcolor='rgba(34, 139, 34, 0.7)'
        ))
        
        supplement_stack = fers_stack + plot_df["FERS_Supplement"]
        fig.add_trace(go.Scatter(
            x=dates, y=supplement_stack,
            mode='none', fill='tonexty', name="FERS Supplement",
            fillcolor='rgba(255, 165, 0, 0.7)'
        ))
        
        tsp_stack = supplement_stack + plot_df["TSP"]
        fig.add_trace(go.Scatter(
            x=dates, y=tsp_stack,
            mode='none', fill='tonexty', name="TSP",
            fillcolor='rgba(219, 112, 147, 0.7)'
        ))
        
        ss_stack = tsp_stack + plot_df["Social_Security"]
        fig.add_trace(go.Scatter(
            x=dates, y=ss_stack,
            mode='none', fill='tonexty', name="Social Security",
            fillcolor='rgba(75, 0, 130, 0.7)'
        ))
        
        # Add net income line after FEHB
        fig.add_trace(go.Scatter(
            x=dates, y=net_income,
            mode='lines', name="Net Income after FEHB",
            line=dict(color='black', width=2)
        ))
        
        # Add FEHB annotations
        annotation_indices = np.linspace(0, len(dates)-1, 8, dtype=int)
        for idx in annotation_indices:
            date = dates.iloc[idx]
            fehb_value = plot_df["FEHB"].iloc[idx]
            fig.add_annotation(
                x=date, y=net_income.iloc[idx],
                text=f"FEHB: ${abs(fehb_value):.0f}",
                showarrow=True,
                arrowhead=4,
                arrowwidth=1,
                arrowcolor='darkred',
                ax=0,
                ay=-30,
                font=dict(color='darkred', size=9)
            )
        
        # Add vertical lines for retirement and social security
        fig.add_vline(x=safe_date_for_plotly(retire_date), line_dash="dash", line_color="red",
                     annotation_text="Retirement", annotation_position="top right")
        fig.add_vline(x=safe_date_for_plotly(ss_date), line_dash="dot", line_color="green",
                     annotation_text="Social Security", annotation_position="top left")
        
        # Add note about FEHB
        fig.add_annotation(
            x=0.03, y=0.03,
            xref="paper", yref="paper",
            text=f"Note: FEHB premiums average ${avg_fehb:.0f}/month and are deducted from total income",
            showarrow=False,
            bgcolor="white",
            opacity=0.8,
            bordercolor="black",
            borderwidth=1,
            borderpad=4,
            font=dict(size=9)
        )
        
        # Format layout
        fig.update_layout(
            title=f"Income Source Breakdown - {scenario_title}",
            xaxis_title="Date",
            yaxis_title="Monthly Income ($)",
            hovermode="x unified",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                tickprefix="$",
                showgrid=True,
                rangemode="nonnegative",
                range=[0, positive_income.max() * 1.1]
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0
            )
        )
        
        return fig
    else:
        # Fallback to matplotlib chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot positive income streams as a stack (excluding FEHB)
        ax.stackplot(dates,
                    plot_df["Salary"],
                    plot_df["FERS"],
                    plot_df["FERS_Supplement"],
                    plot_df["TSP"],
                    plot_df["Social_Security"],
                    labels=["Salary", "FERS Annuity", "FERS Supplement", "TSP", "Social Security"])
        
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

def plot_monthly_income(df_a, df_b, retire_date_a, retire_date_b, ss_date_a, ss_date_b, use_plotly=True):
    """Plot monthly income comparison between two scenarios"""
    # Create dataframe ensuring dates align between scenarios
    # Start by getting common dates - find overlapping dates between the two dataframes
    common_dates = pd.Series(list(set(df_a["Date"]).intersection(set(df_b["Date"]))))    
    common_dates = common_dates.sort_values().reset_index(drop=True)
    
    # Create chart data with only valid dates
    chart_data = pd.DataFrame({
        "Date": common_dates
    })
    
    # Join scenario data based on common dates
    chart_data = chart_data.merge(
        df_a[["Date", "Total_Income"]].rename(columns={"Total_Income": "Scenario A"}),
        on="Date", how="left"
    )
    
    chart_data = chart_data.merge(
        df_b[["Date", "Total_Income"]].rename(columns={"Total_Income": "Scenario B"}),
        on="Date", how="left"
    )
    
    # Drop any rows with NaN values to avoid matplotlib conversion errors
    chart_data = chart_data.dropna()
    
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Add income line traces
        fig.add_trace(go.Scatter(
            x=chart_data["Date"],
            y=chart_data["Scenario A"],
            mode='lines',
            name="Scenario A",
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=chart_data["Date"],
            y=chart_data["Scenario B"],
            mode='lines',
            name="Scenario B",
            line=dict(color='green')
        ))
        
        # Add vertical lines for retirement dates
        fig.add_vline(x=safe_date_for_plotly(retire_date_a), line_dash="dash", line_color="red",
                      annotation_text="A Retirement", annotation_position="top right")
        fig.add_vline(x=safe_date_for_plotly(retire_date_b), line_dash="dash", line_color="green",
                      annotation_text="B Retirement", annotation_position="top right")
        
        # Add vertical lines for social security dates
        fig.add_vline(x=safe_date_for_plotly(ss_date_a), line_dash="dot", line_color="red",
                      annotation_text="A Social Security", annotation_position="top left")
        fig.add_vline(x=safe_date_for_plotly(ss_date_b), line_dash="dot", line_color="green",
                      annotation_text="B Social Security", annotation_position="bottom left")
        
        # Format layout
        fig.update_layout(
            title="Monthly Income Over Time",
            xaxis_title="Date",
            yaxis_title="Monthly Income ($)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True,
                type="date"  # Ensure xaxis is treated as date
            ),
            yaxis=dict(
                tickprefix="$",
                showgrid=True
            ),
        )
        
        return fig
    else:
        # Fallback to matplotlib chart
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

def plot_monthly_delta(delta_df, retire_date_a, retire_date_b, use_plotly=True):
    """Plot monthly income delta between two scenarios"""
    # Drop any NaN values
    clean_df = delta_df.dropna()
    
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Add delta line trace
        fig.add_trace(go.Scatter(
            x=clean_df["Date"],
            y=clean_df["Monthly_Delta"],
            mode='lines',
            name="Monthly Difference",
            line=dict(color='purple')
        ))
        
        # Add zero reference line
        fig.add_hline(y=0, line_color="gray")
        
        # Add vertical lines for retirement dates
        fig.add_vline(x=safe_date_for_plotly(retire_date_a), line_dash="dash", line_color="red",
                     annotation_text="A Retirement", annotation_position="top right")
        fig.add_vline(x=safe_date_for_plotly(retire_date_b), line_dash="dash", line_color="green",
                     annotation_text="B Retirement", annotation_position="top left")
        
        # Format layout
        fig.update_layout(
            title="Monthly Income Difference (B - A)",
            xaxis_title="Date",
            yaxis_title="Monthly Difference ($)",
            hovermode="x unified",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                tickprefix="$",
                showgrid=True,
                zeroline=True,
            )
        )
        
        # Add shaded area for positive/negative regions
        pos_y = clean_df["Monthly_Delta"].copy()
        pos_y[pos_y < 0] = None  # Only show positive values
        
        neg_y = clean_df["Monthly_Delta"].copy()
        neg_y[neg_y > 0] = None  # Only show negative values
        
        fig.add_trace(go.Scatter(
            x=clean_df["Date"], 
            y=pos_y,
            fill='tozeroy', 
            fillcolor='rgba(0,255,0,0.1)',
            line=dict(width=0),
            name="B > A"
        ))
        
        fig.add_trace(go.Scatter(
            x=clean_df["Date"], 
            y=neg_y,
            fill='tozeroy', 
            fillcolor='rgba(255,0,0,0.1)',
            line=dict(width=0),
            name="A > B"
        ))
        
        return fig
        
    else:
        # Fallback to matplotlib chart
        fig, ax = plt.subplots(figsize=(10, 4))
        
        ax.plot(clean_df["Date"], clean_df["Monthly_Delta"], color='purple')
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
                          breakeven_date=None, breakeven_value=None, breakeven_idx=None, use_plotly=True):
    """Plot cumulative income comparison with breakeven point"""
    # Create common dataframe with aligned dates
    common_dates = pd.Series(list(set(df_a["Date"]).intersection(set(df_b["Date"]))))    
    common_dates = common_dates.sort_values().reset_index(drop=True)
    
    # Create chart data with only valid dates
    chart_data = pd.DataFrame({
        "Date": common_dates
    })
    
    # Join cumulative income data based on common dates
    chart_data = chart_data.merge(
        df_a[["Date", "Cumulative_Income"]].rename(columns={"Cumulative_Income": "A_Cumulative"}),
        on="Date", how="left"
    )
    
    chart_data = chart_data.merge(
        df_b[["Date", "Cumulative_Income"]].rename(columns={"Cumulative_Income": "B_Cumulative"}),
        on="Date", how="left"
    )
    
    # Drop any rows with NaN values
    chart_data = chart_data.dropna()
    
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Add cumulative income traces
        fig.add_trace(go.Scatter(
            x=chart_data["Date"],
            y=chart_data["A_Cumulative"],
            mode='lines',
            name="Scenario A",
            line=dict(color='royalblue', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=chart_data["Date"],
            y=chart_data["B_Cumulative"],
            mode='lines',
            name="Scenario B",
            line=dict(color='forestgreen', width=2)
        ))
        
        # Add retirement date lines
        fig.add_vline(x=safe_date_for_plotly(retire_date_a), line_dash="dash", line_color="red", 
                    annotation_text="A Retirement", annotation_position="top right")
        fig.add_vline(x=safe_date_for_plotly(retire_date_b), line_dash="dash", line_color="green", 
                    annotation_text="B Retirement", annotation_position="top left")
        
        # Add breakeven point if exists
        if breakeven_date and breakeven_value and breakeven_idx is not None:
            # Check if breakeven date is in chart_data
            if breakeven_date in chart_data["Date"].values:
                fig.add_trace(go.Scatter(
                    x=[breakeven_date],
                    y=[breakeven_value],
                    mode='markers',
                    marker=dict(size=12, color='black'),
                    name="Breakeven Point",
                    hoverinfo="x+y"
                ))
                
                # Add annotation
                fig.add_annotation(
                    x=breakeven_date,
                    y=breakeven_value,
                    text=f"Breakeven: {breakeven_date.strftime('%b %Y')}",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    ax=30,
                    ay=-30
                )
        
        # Format layout
        fig.update_layout(
            title="Cumulative Income Over Time",
            xaxis_title="Date",
            yaxis_title="Cumulative Income ($)",
            hovermode="x unified",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                tickprefix="$",
                showgrid=True
            )
        )
        
        return fig
    else:
        # Fallback to matplotlib chart
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(chart_data["Date"], chart_data["A_Cumulative"], label="Scenario A")
        ax.plot(chart_data["Date"], chart_data["B_Cumulative"], label="Scenario B")
        
        # Add retirement date lines
        ax.axvline(x=retire_date_a, color='r', linestyle='--', label="A Retirement")
        ax.axvline(x=retire_date_b, color='g', linestyle='--', label="B Retirement")
        
        # Add breakeven point if exists
        if breakeven_date and breakeven_value and breakeven_idx is not None:
            # Check if breakeven date is in chart_data
            if breakeven_date in chart_data["Date"].values:
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

def plot_household_income(dates, combined_income, retire_date_a, retire_date_b, ss_date_a, ss_date_b, use_plotly=True):
    """Plot combined household monthly income"""
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Add income line trace
        fig.add_trace(go.Scatter(
            x=dates,
            y=combined_income,
            mode='lines',
            name="Combined Monthly Income",
            line=dict(color='purple', width=2)
        ))
        
        # Add vertical lines for retirement dates
        fig.add_vline(x=safe_date_for_plotly(retire_date_a), line_dash="dash", line_color="red",
                     annotation_text="A Retirement", annotation_position="top right")
        fig.add_vline(x=safe_date_for_plotly(retire_date_b), line_dash="dash", line_color="green",
                     annotation_text="B Retirement", annotation_position="top left")
        
        # Add vertical lines for social security dates
        fig.add_vline(x=safe_date_for_plotly(ss_date_a), line_dash="dot", line_color="red",
                     annotation_text="A Social Security", annotation_position="bottom right")
        fig.add_vline(x=safe_date_for_plotly(ss_date_b), line_dash="dot", line_color="green",
                     annotation_text="B Social Security", annotation_position="bottom left")
        
        # Format layout
        fig.update_layout(
            title="Combined Household Monthly Income",
            xaxis_title="Date",
            yaxis_title="Monthly Income ($)",
            hovermode="x unified",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                tickprefix="$",
                showgrid=True
            )
        )
        
        return fig
    else:
        # Fallback to matplotlib chart
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

def plot_combined_sources(combined_sources, retire_date_a, retire_date_b, use_plotly=True):
    """Plot stacked area chart for combined income sources with FEHB as expense"""
    # Get dates from the combined_sources dataframe
    dates = combined_sources["Date"]
    
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
    
    # Calculate average FEHB expense
    avg_fehb = abs(combined_sources["FEHB"].mean())
    
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Add stacked area traces for income sources
        fig.add_trace(go.Scatter(
            x=dates, y=combined_sources["Salary"],
            mode='none', fill='tozeroy', name="Salary",
            fillcolor='rgba(65, 105, 225, 0.7)'
        ))
        
        # Calculate cumulative sums for proper stacking
        fers_stack = combined_sources["Salary"] + combined_sources["FERS"]
        fig.add_trace(go.Scatter(
            x=dates, y=fers_stack,
            mode='none', fill='tonexty', name="FERS Annuity",
            fillcolor='rgba(34, 139, 34, 0.7)'
        ))
        
        supplement_stack = fers_stack + combined_sources["FERS_Supplement"]
        fig.add_trace(go.Scatter(
            x=dates, y=supplement_stack,
            mode='none', fill='tonexty', name="FERS Supplement",
            fillcolor='rgba(255, 165, 0, 0.7)'
        ))
        
        tsp_stack = supplement_stack + combined_sources["TSP"]
        fig.add_trace(go.Scatter(
            x=dates, y=tsp_stack,
            mode='none', fill='tonexty', name="TSP",
            fillcolor='rgba(219, 112, 147, 0.7)'
        ))
        
        ss_stack = tsp_stack + combined_sources["Social_Security"]
        fig.add_trace(go.Scatter(
            x=dates, y=ss_stack,
            mode='none', fill='tonexty', name="Social Security",
            fillcolor='rgba(75, 0, 130, 0.7)'
        ))
        
        # Add net income line after FEHB
        fig.add_trace(go.Scatter(
            x=dates, y=net_income,
            mode='lines', name="Net Income after FEHB",
            line=dict(color='black', width=2)
        ))
        
        # Add FEHB annotations
        annotation_indices = np.linspace(0, len(dates)-1, 8, dtype=int)
        for idx in annotation_indices:
            date = dates.iloc[idx]
            fehb_value = combined_sources["FEHB"].iloc[idx]
            fig.add_annotation(
                x=date, y=net_income.iloc[idx],
                text=f"FEHB: ${abs(fehb_value):.0f}",
                showarrow=True,
                arrowhead=4,
                arrowwidth=1,
                arrowcolor='darkred',
                ax=0,
                ay=-30,
                font=dict(color='darkred', size=9)
            )
        
        # Add vertical lines for retirement dates
        fig.add_vline(x=safe_date_for_plotly(retire_date_a), line_dash="dash", line_color="red",
                     annotation_text="A Retirement", annotation_position="top right")
        fig.add_vline(x=safe_date_for_plotly(retire_date_b), line_dash="dash", line_color="green",
                     annotation_text="B Retirement", annotation_position="top left")
        
        # Add note about FEHB
        fig.add_annotation(
            x=0.03, y=0.03,
            xref="paper", yref="paper",
            text=f"Note: FEHB premiums average ${avg_fehb:.0f}/month and are deducted from total income",
            showarrow=False,
            bgcolor="white",
            opacity=0.8,
            bordercolor="black",
            borderwidth=1,
            borderpad=4,
            font=dict(size=9)
        )
        
        # Format layout
        fig.update_layout(
            title="Combined Household Income Sources",
            xaxis_title="Date",
            yaxis_title="Monthly Income ($)",
            hovermode="x unified",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                tickprefix="$",
                showgrid=True,
                rangemode="nonnegative",
                range=[0, positive_income.max() * 1.1]
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0
            )
        )
        
        return fig
    else:
        # Fallback to matplotlib chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot income sources (excluding FEHB)
        ax.stackplot(combined_sources["Date"],
                    combined_sources["Salary"],
                    combined_sources["FERS"],
                    combined_sources["FERS_Supplement"],
                    combined_sources["TSP"],
                    combined_sources["Social_Security"],
                    labels=["Salary", "FERS Annuity", "FERS Supplement", "TSP", "Social Security"])
        
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

def plot_cumulative_household(dates, combined_cumulative, retire_date_a, retire_date_b, use_plotly=True):
    """Plot cumulative household income"""
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Add cumulative income trace
        fig.add_trace(go.Scatter(
            x=dates,
            y=combined_cumulative,
            mode='lines',
            name="Combined Cumulative Income",
            line=dict(color='green', width=2)
        ))
        
        # Add vertical lines for retirement dates
        fig.add_vline(x=safe_date_for_plotly(retire_date_a), line_dash="dash", line_color="red",
                     annotation_text="A Retirement", annotation_position="top right")
        fig.add_vline(x=safe_date_for_plotly(retire_date_b), line_dash="dash", line_color="green",
                     annotation_text="B Retirement", annotation_position="top left")
        
        # Format layout
        fig.update_layout(
            title="Combined Cumulative Household Income",
            xaxis_title="Date",
            yaxis_title="Cumulative Income ($)",
            hovermode="x unified",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                tickprefix="$",
                showgrid=True
            )
        )
        
        return fig
    else:
        # Fallback to matplotlib chart
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

def plot_income_ratio(income_ratio, retire_date_a, retire_date_b, use_plotly=True):
    """Plot income ratio analysis"""
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Add stacked area traces for income ratios
        fig.add_trace(go.Scatter(
            x=income_ratio["Date"],
            y=income_ratio["Fixed_Income_Ratio"] * 100,
            mode='none',
            fill='tozeroy',
            name="Fixed Income (FERS + SS)",
            fillcolor='rgba(34, 139, 34, 0.7)'
        ))
        
        # For proper stacking, add a trace that's the sum of both
        fig.add_trace(go.Scatter(
            x=income_ratio["Date"],
            y=(income_ratio["Fixed_Income_Ratio"] + income_ratio["Variable_Income_Ratio"]) * 100,
            mode='none',
            fill='tonexty',
            name="Variable Income (TSP)",
            fillcolor='rgba(219, 112, 147, 0.7)'
        ))
        
        # Add vertical lines for retirement dates
        fig.add_vline(x=safe_date_for_plotly(retire_date_a), line_dash="dash", line_color="red",
                     annotation_text="A Retirement", annotation_position="top right")
        fig.add_vline(x=safe_date_for_plotly(retire_date_b), line_dash="dash", line_color="green",
                     annotation_text="B Retirement", annotation_position="top left")
        
        # Format layout
        fig.update_layout(
            title="Income Source Ratio",
            xaxis_title="Date",
            yaxis_title="Percentage of Total Income (%)",
            hovermode="x unified",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                showgrid=True,
                range=[0, 100]
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0
            )
        )
        
        return fig
    else:
        # Fallback to matplotlib chart
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

def plot_tsp_balance(df, retire_date, use_plotly=True):
    """Plot TSP balance over time"""
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Add TSP balance line
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["TSP_Balance"],
            mode='lines',
            name="TSP Balance",
            line=dict(color='green', width=2)
        ))
        
        # Add retirement date line
        fig.add_vline(x=safe_date_for_plotly(retire_date), line_dash="dash", line_color="red",
                     annotation_text="Retirement", annotation_position="top right")
        
        # Format layout
        fig.update_layout(
            title="TSP Balance Over Time",
            xaxis_title="Date",
            yaxis_title="Balance ($)",
            hovermode="x unified",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                tickprefix="$",
                showgrid=True
            )
        )
        
        return fig
    else:
        # Fallback to matplotlib chart
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

def plot_rmd_vs_withdrawal(df, retire_date, use_plotly=True):
    """Plot RMD vs actual withdrawal rate"""
    # Calculate actual withdrawal amount (pre-tax)
    withdrawal = df["TSP"] / (1 - 0.22)  # Approximate pre-tax withdrawal
    
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Add RMD and withdrawal lines
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["RMD_Amount"],
            mode='lines',
            name="Required Minimum Distribution",
            line=dict(color='red', dash='dash')
        ))
        
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=withdrawal,
            mode='lines',
            name="Actual Withdrawal",
            line=dict(color='blue')
        ))
        
        # Add retirement date line
        fig.add_vline(x=safe_date_for_plotly(retire_date), line_dash="dash", line_color="green",
                     annotation_text="Retirement", annotation_position="top right")
        
        # Format layout
        fig.update_layout(
            title="RMD vs Actual TSP Withdrawal",
            xaxis_title="Date",
            yaxis_title="Monthly Amount ($)",
            hovermode="x unified",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                tickprefix="$",
                showgrid=True
            )
        )
        
        return fig
    else:
        # Fallback to matplotlib chart
        fig, ax = plt.subplots(figsize=(10, 5))
        
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

def plot_cash_flow(df, retire_date, use_plotly=True):
    """Plot cash flow analysis with expenses"""
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Add income, expenses, and net cash flow lines
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["Total_Income"],
            mode='lines',
            name="Total Income",
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["Monthly_Expenses"],
            mode='lines',
            name="Monthly Expenses",
            line=dict(color='red')
        ))
        
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["Net_Cash_Flow"],
            mode='lines',
            name="Net Cash Flow",
            line=dict(color='green')
        ))
        
        # Add horizontal line at zero
        fig.add_hline(y=0, line_color="gray", line_dash="dash")
        
        # Add retirement date line
        fig.add_vline(x=safe_date_for_plotly(retire_date), line_dash="dash", line_color="purple",
                     annotation_text="Retirement", annotation_position="top right")
        
        # Format layout
        fig.update_layout(
            title="Monthly Cash Flow Analysis",
            xaxis_title="Date",
            yaxis_title="Amount ($)",
            hovermode="x unified",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                tickprefix="$",
                showgrid=True
            )
        )
        
        return fig
    else:
        # Fallback to matplotlib chart
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

def plot_cumulative_cash_flow(df, retire_date, use_plotly=True):
    """Plot cumulative cash flow over time"""
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Add cumulative cash flow line
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["Cumulative_Cash_Flow"],
            mode='lines',
            name="Cumulative Cash Flow",
            line=dict(color='green', width=2)
        ))
        
        # Add horizontal line at zero
        fig.add_hline(y=0, line_color="gray", line_dash="dash")
        
        # Add retirement date line
        fig.add_vline(x=safe_date_for_plotly(retire_date), line_dash="dash", line_color="red",
                     annotation_text="Retirement", annotation_position="top right")
        
        # Format layout
        fig.update_layout(
            title="Cumulative Cash Flow Over Time",
            xaxis_title="Date",
            yaxis_title="Cumulative Amount ($)",
            hovermode="x unified",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                tickprefix="$",
                showgrid=True
            )
        )
        
        return fig
    else:
        # Fallback to matplotlib chart
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

def plot_stress_test_comparison(results, retire_date, use_plotly=True):
    """Plot comparison of different market scenarios"""
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Plot the different scenarios
        fig.add_trace(go.Scatter(
            x=results["best_case"]["Date"],
            y=results["best_case"]["Total_Income"],
            mode='lines',
            name="Best Case",
            line=dict(color='green')
        ))
        
        fig.add_trace(go.Scatter(
            x=results["average_case"]["Date"],
            y=results["average_case"]["Total_Income"],
            mode='lines',
            name="Average Case",
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=results["worst_case"]["Date"],
            y=results["worst_case"]["Total_Income"],
            mode='lines',
            name="Worst Case",
            line=dict(color='red')
        ))
        
        # Add retirement date line
        fig.add_vline(x=safe_date_for_plotly(retire_date), line_dash="dash", line_color="purple",
                     annotation_text="Retirement", annotation_position="top right")
        
        # Format layout
        fig.update_layout(
            title="Income Under Different Market Scenarios",
            xaxis_title="Date",
            yaxis_title="Monthly Income ($)",
            hovermode="x unified",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                tickprefix="$",
                showgrid=True
            )
        )
        
        return fig
    else:
        # Fallback to matplotlib chart
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

def plot_tsp_stress_test(results, retire_date, use_plotly=True):
    """Plot TSP balance under different market scenarios"""
    if use_plotly:
        # Create interactive plotly chart
        fig = go.Figure()
        
        # Plot the different scenarios
        fig.add_trace(go.Scatter(
            x=results["best_case"]["Date"],
            y=results["best_case"]["TSP_Balance"],
            mode='lines',
            name="Best Case",
            line=dict(color='green')
        ))
        
        fig.add_trace(go.Scatter(
            x=results["average_case"]["Date"],
            y=results["average_case"]["TSP_Balance"],
            mode='lines',
            name="Average Case",
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=results["worst_case"]["Date"],
            y=results["worst_case"]["TSP_Balance"],
            mode='lines',
            name="Worst Case",
            line=dict(color='red')
        ))
        
        # Add retirement date line
        fig.add_vline(x=safe_date_for_plotly(retire_date), line_dash="dash", line_color="purple",
                     annotation_text="Retirement", annotation_position="top right")
        
        # Format layout
        fig.update_layout(
            title="TSP Balance Under Different Market Scenarios",
            xaxis_title="Date",
            yaxis_title="TSP Balance ($)",
            hovermode="x unified",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                showgrid=True
            ),
            yaxis=dict(
                tickprefix="$",
                showgrid=True
            )
        )
        
        return fig
    else:
        # Fallback to matplotlib chart
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
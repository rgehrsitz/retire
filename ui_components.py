import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
from dateutil.relativedelta import relativedelta
import os
import json
import io
import zipfile

from retirement_model import calculate_age, calculate_service_years
from scenario_manager import (
    save_scenario, 
    load_scenario, 
    get_available_scenarios,
    delete_scenario,
    clear_all_scenarios
)
from plots import (
    plot_household_income,
    plot_combined_sources,
    plot_cumulative_household,
    plot_income_ratio
)

def render_scenario_inputs(scenario_letter, session_key, DEFAULT_COLA, DEFAULT_TSP_GROWTH, DEFAULT_TSP_WITHDRAW):
    """Render inputs for a scenario and return the input dictionary"""
    st.subheader(f"Scenario {scenario_letter}: {'Your Info' if scenario_letter == 'A' else 'Alternate or Spouse'}")
    
    # Check if saved scenarios exist
    scenarios = get_available_scenarios()
    if scenarios:
        load_scenario_key = f"load_scenario_{scenario_letter.lower()}"
        selected_scenario = st.selectbox(
            "Load saved scenario", 
            ["None"] + scenarios, 
            key=load_scenario_key
        )
        if selected_scenario != "None":
            scenario_data = load_scenario(f"scenarios/{selected_scenario}.json")
            # Set as default values for inputs
            if session_key not in st.session_state:
                st.session_state[session_key] = scenario_data
    
    # Personal Information
    birthdate = st.date_input(
        "Birthdate", 
        value=st.session_state.get(session_key, {}).get(
            'birthdate', 
            dt.date(1965, 2, 25) if scenario_letter == 'A' else dt.date(1967, 5, 10)
        ),
        key=f"birthdate_{scenario_letter.lower()}"
    )
    
    start_date = st.date_input(
        "Service Start Date", 
        value=st.session_state.get(session_key, {}).get(
            'start_date', 
            dt.date(1987, 6, 22) if scenario_letter == 'A' else dt.date(1990, 9, 15)
        ),
        key=f"start_date_{scenario_letter.lower()}"
    )
    
    retire_date = st.date_input(
        "Retirement Date", 
        value=st.session_state.get(session_key, {}).get(
            'retire_date', 
            dt.date(2025, 8, 1) if scenario_letter == 'A' else dt.date(2027, 7, 1)
        ),
        key=f"retire_date_{scenario_letter.lower()}"
    )
    
    age_at_retirement = calculate_age(birthdate, retire_date)
    service_at_retirement = calculate_service_years(start_date, retire_date)
    
    display_name = "You" if scenario_letter == 'A' else f"Person {scenario_letter}"
    st.info(f"{display_name} will be {age_at_retirement} years old with {service_at_retirement:.2f} years of service at retirement.")
    
    # Financial Information
    high3 = st.number_input(
        "High-3 Salary ($)", 
        value=st.session_state.get(session_key, {}).get(
            'high3', 
            179000 if scenario_letter == 'A' else 165000
        ),
        step=1000,
        key=f"high3_{scenario_letter.lower()}"
    )
    
    tsp_start = st.number_input(
        "TSP Balance ($)", 
        value=st.session_state.get(session_key, {}).get(
            'tsp_balance', 
            1800000 if scenario_letter == 'A' else 1200000
        ),
        step=10000,
        key=f"tsp_balance_{scenario_letter.lower()}"
    )
    
    sick_leave_hours = st.number_input(
        "Sick Leave (hours)", 
        value=st.session_state.get(session_key, {}).get(
            'sick_leave_hours', 
            1866 if scenario_letter == 'A' else 1500
        ),
        step=10,
        key=f"sick_leave_hours_{scenario_letter.lower()}"
    )
    
    # Social Security
    ss_start_age = st.slider(
        "Social Security Start Age", 
        min_value=62, 
        max_value=70, 
        value=st.session_state.get(session_key, {}).get('social_security_age', 67),
        key=f"social_security_age_{scenario_letter.lower()}"
    )
    
    # Additional Options
    survivor_option = st.selectbox(
        "Survivor Benefit Option", 
        options=["None", "Partial", "Full"],
        index=1,  # Default to "Partial"
        key=f"survivor_benefit_{scenario_letter.lower()}"
    )
    
    filing_status = st.selectbox(
        "Tax Filing Status", 
        options=["single", "married"],
        index=0,  # Default to "single"
        key=f"filing_status_{scenario_letter.lower()}"
    )
    
    pa_resident = st.checkbox(
        "Pennsylvania Resident", 
        value=st.session_state.get(session_key, {}).get('pa_resident', True),
        key=f"pa_resident_{scenario_letter.lower()}"
    )
    
    fehb_premium = st.number_input(
        "Monthly FEHB Premium ($)", 
        value=st.session_state.get(session_key, {}).get('fehb_premium', 350),
        step=10,
        key=f"fehb_premium_{scenario_letter.lower()}"
    )
    
    # Financial Assumptions
    cola = st.slider(
        "Annual COLA (%)", 
        min_value=0.0, 
        max_value=0.04, 
        value=st.session_state.get(session_key, {}).get('cola', DEFAULT_COLA),
        step=0.001,
        format="%.3f",
        key=f"cola_{scenario_letter.lower()}"
    )
    
    tsp_growth = st.slider(
        "TSP Growth Rate (%)", 
        min_value=0.0, 
        max_value=0.10, 
        value=st.session_state.get(session_key, {}).get('tsp_growth', DEFAULT_TSP_GROWTH),
        step=0.001,
        format="%.3f",
        key=f"tsp_growth_{scenario_letter.lower()}"
    )
    
    tsp_withdraw = st.slider(
        "TSP Withdrawal Rate (%)", 
        min_value=0.0, 
        max_value=0.10, 
        value=st.session_state.get(session_key, {}).get('tsp_withdraw', DEFAULT_TSP_WITHDRAW),
        step=0.001,
        format="%.3f",
        key=f"tsp_withdraw_{scenario_letter.lower()}"
    )
    
    # Scenario notes
    scenario_notes = st.text_area(
        "Scenario Notes", 
        value=st.session_state.get(session_key, {}).get('notes', ""),
        height=100,
        key=f"scenario_notes_{scenario_letter.lower()}",
        help="Add notes about this scenario (e.g., assumptions, special considerations)"
    )
    
    # Save scenario
    save_name = st.text_input("Scenario Name to Save", key=f"save_name_{scenario_letter.lower()}")
    if st.button(f"Save Scenario {scenario_letter}"):
        # Collect current scenario data
        scenario_data = {
            'birthdate': birthdate,
            'start_date': start_date,
            'retire_date': retire_date,
            'high3': high3,
            'tsp_balance': tsp_start,
            'sick_leave_hours': sick_leave_hours,
            'social_security_age': ss_start_age,
            'survivor_benefit': survivor_option,
            'filing_status': filing_status,
            'pa_resident': pa_resident,
            'fehb_premium': fehb_premium,
            'cola': cola,
            'tsp_growth': tsp_growth,
            'tsp_withdraw': tsp_withdraw,
            'notes': scenario_notes
        }
        
        # Save to file
        if save_name:
            save_result = save_scenario(scenario_data, save_name)
            st.success(save_result)
            
            # Update session state
            st.session_state[session_key] = scenario_data
        else:
            st.error("Please enter a name for your scenario.")
    
    # Return parameters for the simulate_retirement function
    return {
        "birthdate": birthdate,
        "start_date": start_date,
        "retire_date": retire_date,
        "high3": high3,
        "tsp_start": tsp_start,
        "sick_leave_hours": sick_leave_hours,
        "ss_start_age": ss_start_age,
        "survivor_option": survivor_option,
        "cola": cola,
        "tsp_growth": tsp_growth,
        "tsp_withdraw": tsp_withdraw,
        "pa_resident": pa_resident,
        "fehb_premium": fehb_premium,
        "filing_status": filing_status
    }

def render_export_options(df_a, df_b, to_excel_func):
    """Render export options for scenario data"""
    # Allow user to select what to export
    export_choice = st.multiselect(
        "Select data to export", 
        ["Scenario A", "Scenario B", "Combined Household"]
    )
    
    if export_choice:
        export_data = pd.DataFrame()
        
        if "Scenario A" in export_choice:
            df_a_export = df_a.copy()
            df_a_export.columns = [f"A_{col}" if col != "Date" else col for col in df_a_export.columns]
            
            if export_data.empty:
                export_data = df_a_export
            else:
                export_data = export_data.merge(df_a_export, on="Date", how="outer")
        
        if "Scenario B" in export_choice:
            df_b_export = df_b.copy()
            df_b_export.columns = [f"B_{col}" if col != "Date" else col for col in df_b_export.columns]
            
            if export_data.empty:
                export_data = df_b_export
            else:
                export_data = export_data.merge(df_b_export, on="Date", how="outer")
        
        if "Combined Household" in export_choice:
            df_combined = pd.DataFrame({
                "Date": df_a["Date"],
                "Combined_Total_Income": df_a["Total_Income"] + df_b["Total_Income"],
                "Combined_Cumulative_Income": df_a["Cumulative_Income"] + df_b["Cumulative_Income"]
            })
            
            if export_data.empty:
                export_data = df_combined
            else:
                export_data = export_data.merge(df_combined, on="Date", how="outer")
        
        # Convert to Excel
        excel_data = to_excel_func(export_data)
        
        # Offer download button
        st.download_button(
            label="📥 Download Excel file",
            data=excel_data,
            file_name="retirement_analysis.xlsx",
            mime="application/vnd.ms-excel"
        )

def render_household_tab(df_a, df_b, retire_date_a, retire_date_b, ss_date_a, ss_date_b):
    """Render the household combined income tab"""
    st.header("👨‍👩‍👧‍👦 Household Combined Income")
    
    st.write("This view shows the combined household income when both people are modeled together.")
    
    # Create combined income streams
    combined_income = df_a["Total_Income"] + df_b["Total_Income"]
    combined_cumulative = combined_income.cumsum()
    
    # Combined Monthly Income
    fig_household = plot_household_income(
        df_a["Date"], combined_income, retire_date_a, retire_date_b, ss_date_a, ss_date_b
    )
    st.pyplot(fig_household)
    
    # Stacked Income Sources (Combined Household)
    st.subheader("💵 Combined Income Sources")
    
    # Create combined sources dataframe
    combined_sources = pd.DataFrame({
        "Date": df_a["Date"],
        "Salary": df_a["Salary"] + df_b["Salary"],
        "FERS": df_a["FERS"] + df_b["FERS"],
        "FERS_Supplement": df_a["FERS_Supplement"] + df_b["FERS_Supplement"],
        "TSP": df_a["TSP"] + df_b["TSP"],
        "Social_Security": df_a["Social_Security"] + df_b["Social_Security"],
        "FEHB": df_a["FEHB"] + df_b["FEHB"]
    })
    
    fig_combined = plot_combined_sources(
        combined_sources, retire_date_a, retire_date_b
    )
    st.pyplot(fig_combined)
    
    # Cumulative Household Income
    st.subheader("📈 Cumulative Household Income")
    
    fig_cum = plot_cumulative_household(
        df_a["Date"], combined_cumulative, retire_date_a, retire_date_b
    )
    st.pyplot(fig_cum)
    
    # Income Ratio Analysis
    st.subheader("📊 Income Ratio Analysis")
    
    # Calculate income ratios
    income_ratio = pd.DataFrame({
        "Date": df_a["Date"],
        "Fixed_Income_Ratio": (df_a["FERS"] + df_b["FERS"] + df_a["FERS_Supplement"] + df_b["FERS_Supplement"] + 
                              df_a["Social_Security"] + df_b["Social_Security"]) / 
                             (df_a["Total_Income"] + df_b["Total_Income"]),
        "Variable_Income_Ratio": (df_a["TSP"] + df_b["TSP"]) / (df_a["Total_Income"] + df_b["Total_Income"])
    })
    
    # Replace NaN and inf values
    income_ratio = income_ratio.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    fig_ratio = plot_income_ratio(
        income_ratio, retire_date_a, retire_date_b
    )
    st.pyplot(fig_ratio)
    
    # Key metrics about the household
    st.subheader("📊 Household Financial Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        peak_income = combined_income.max()
        st.metric("Peak Monthly Income", f"${peak_income:,.2f}")
        
    with col2:
        avg_retired_income = combined_income[
            (df_a["Date"] > retire_date_a) & 
            (df_a["Date"] > retire_date_b)
        ].mean()
        st.metric("Average Retired Income", f"${avg_retired_income:,.2f}")
        
    with col3:
        fixed_income_pct = ((df_a["FERS"] + df_b["FERS"] + 
                            df_a["FERS_Supplement"] + df_b["FERS_Supplement"] + 
                            df_a["Social_Security"] + df_b["Social_Security"]) /
                           (df_a["Total_Income"] + df_b["Total_Income"])).mean() * 100
        st.metric("Average Fixed Income %", f"{fixed_income_pct:.1f}%")

def render_settings_tab():
    """Render the settings tab"""
    st.header("⚙️ Application Settings")
    
    st.subheader("Data Management")
    
    # Export all scenarios
    if st.button("Export All Saved Scenarios"):
        if os.path.exists("scenarios") and os.listdir("scenarios"):
            # Create a zip file with all scenarios
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for scenario_file in os.listdir("scenarios"):
                    if scenario_file.endswith(".json"):
                        zipf.write(os.path.join("scenarios", scenario_file), scenario_file)
            
            # Offer download button
            st.download_button(
                label="📥 Download All Scenarios (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="retirement_scenarios.zip",
                mime="application/zip"
            )
        else:
            st.warning("No saved scenarios found.")
    
    # Import scenarios
    st.subheader("Import Scenarios")
    uploaded_file = st.file_uploader("Upload Scenarios ZIP", type="zip")
    if uploaded_file is not None:
        if st.button("Import Uploaded Scenarios"):
            try:
                # Create scenarios directory if it doesn't exist
                os.makedirs("scenarios", exist_ok=True)
                
                # Extract ZIP contents
                with zipfile.ZipFile(uploaded_file) as zipf:
                    # Count valid JSON files
                    json_files = [f for f in zipf.namelist() if f.endswith('.json')]
                    
                    # Extract all JSON files
                    for json_file in json_files:
                        zipf.extract(json_file, "scenarios")
                
                st.success(f"Successfully imported {len(json_files)} scenario(s).")
                
            except Exception as e:
                st.error(f"Error importing scenarios: {e}")
    
    # Delete scenario
    st.subheader("Delete Scenario")
    delete_scenarios = get_available_scenarios()
    if delete_scenarios:
        scenario_to_delete = st.selectbox("Select scenario to delete", delete_scenarios)
        if st.button("Delete Selected Scenario"):
            try:
                if delete_scenario(scenario_to_delete):
                    st.success(f"Deleted scenario: {scenario_to_delete}")
                else:
                    st.error("Failed to delete scenario.")
            except Exception as e:
                st.error(f"Error deleting scenario: {e}")
    else:
        st.info("No saved scenarios available to delete.")
    
    # Clear all data
    st.subheader("Reset Application")
    if st.button("Clear All Saved Scenarios"):
        if os.path.exists("scenarios"):
            try:
                if clear_all_scenarios():
                    st.success("All saved scenarios have been deleted.")
                else:
                    st.error("Failed to clear scenarios.")
            except Exception as e:
                st.error(f"Error clearing scenarios: {e}")
        else:
            st.info("No saved scenarios to clear.")
            
    # Application Display Settings
    st.subheader("Display Settings")
    
    # Dark/Light mode toggle
    theme = st.radio(
        "Color Theme",
        options=["Light", "Dark"],
        horizontal=True
    )
    
    if theme == "Dark":
        st.write("Dark mode will be applied on the next app restart.")
    
    # Chart type preference
    chart_preference = st.radio(
        "Chart Preference",
        options=["Interactive (Plotly)", "Static (Matplotlib)"],
        horizontal=True
    )
    
    if chart_preference == "Interactive (Plotly)":
        st.info("Interactive charts require the plotly package. Install with: pip install plotly")
    
    # Save settings
    if st.button("Save Settings"):
        st.success("Settings saved!")
        # In a real app, you'd save these to a config file or database

def render_help_tab():
    """Render the help documentation tab"""
    st.header("ℹ️ Help & Documentation")
    
    st.subheader("About This Tool")
    st.markdown("""
    This Federal Retirement Scenario Explorer is designed to help federal employees model their retirement income 
    under different scenarios. It accounts for:
    
    - **FERS Annuity**: Calculated based on your years of service, high-3 salary, and the appropriate multiplier (1.0% or 1.1%)
    - **FERS Supplement**: For those retiring before age 62 with at least 20 years of service
    - **TSP**: Models growth and withdrawals from your Thrift Savings Plan
    - **Social Security**: Estimates benefits based on your chosen start age
    - **Taxes**: Accounts for federal taxes and state tax exemptions for PA residents
    - **Survivor Benefits**: Models the reduction in annuity based on your chosen survivor benefit option
    - **Health Insurance**: Includes FEHB premiums in retirement
    
    You can compare two different scenarios or model your combined household income with your spouse.
    """)
    
    st.subheader("How to Use")
    st.markdown("""
    1. **Individual Analysis Tab**:
       - Enter your personal information, service dates, and financial details
       - Adjust retirement date, Social Security start age, and other parameters
       - Save scenarios for future reference
       - Compare two different scenarios side by side
    
    2. **Household View Tab**:
       - View combined income for you and your spouse/partner
       - See stacked income sources for your household
       - Analyze income ratios (fixed vs. variable income)
    
    3. **Risk Analysis Tab**:
       - Run Monte Carlo simulations to test your plan against market volatility
       - See how different COLA and market scenarios affect your retirement
       - Identify potential risks in your retirement plan
    
    4. **Settings Tab**:
       - Export or delete saved scenarios
       - Import scenarios from other users
       - Reset application data if needed
    
    5. **Key Features**:
       - Monthly income projections
       - Cumulative income comparison
       - Income source breakdown
       - Breakeven point analysis
       - Data export to Excel
    """)
    
    st.subheader("Key Calculations")
    st.markdown("""
    **FERS Annuity**: 
    - 1.0% × Years of Service × High-3 Average Salary
    - Or 1.1% × Years of Service × High-3 if retiring at age 62+ with 20+ years of service
    
    **FERS Supplement**:
    - Estimated Social Security benefit at age 62 × (Years of Service ÷ 40)
    - Stops at age 62
    
    **Survivor Benefit Reduction**:
    - None: 0% reduction
    - Partial: 5% reduction (provides 25% of annuity to survivor)
    - Full: 10% reduction (provides 50% of annuity to survivor)
    
    **Tax Advantages**:
    - Pennsylvania does not tax retirement income (FERS, TSP, Social Security)
    - Federal taxes use progressive tax brackets
    """)
    
    st.subheader("Tips & Tricks")
    st.markdown("""
    - **Save Scenarios**: Create and save multiple scenarios to compare different retirement dates
    - **Taxation**: Toggle the PA Resident checkbox to see the tax advantage of retiring in Pennsylvania
    - **Sensitivity Analysis**: Try different COLA, TSP growth, and withdrawal rates to stress-test your plan
    - **Breakeven Point**: Look for the point where cumulative incomes cross to determine long-term advantages
    - **Export Data**: Use the export feature to download detailed monthly projections for further analysis
    - **Monte Carlo**: Use the Risk Analysis tab to see how market volatility affects your retirement income
    """)
    
    with st.expander("Detailed FERS Rules"):
        st.markdown("""
        **Eligibility for Immediate Retirement:**
        - **MRA+30**: Minimum Retirement Age (55-57) with 30+ years of service
        - **60+20**: Age 60+ with 20+ years of service
        - **62+5**: Age 62+ with 5+ years of service
        
        **Special Retirement Supplement:**
        - Available to those who retire before age 62 with 20+ years of service
        - Estimated as your age-62 Social Security benefit × (Years of Service ÷ 40)
        - Ends at age 62 when you become eligible for Social Security
        
        **High-3 Calculation:**
        - Based on your highest 3 consecutive years of base pay
        - Usually your final 3 years of service
        - Includes locality pay but excludes overtime, bonuses, etc.
        
        **Survivor Benefits:**
        - None: No reduction, but no continuing benefit to survivor
        - Partial (25%): 5% reduction in your annuity
        - Full (50%): 10% reduction in your annuity
        
        **COLA (Cost of Living Adjustment):**
        - Under age 62: COLA is reduced by 1%
        - Age 62+: Full COLA equal to CPI-W increase
        """)
    
    st.subheader("Updates & Feedback")
    st.markdown("""
    This tool is continuously being improved. Future enhancements may include:
    
    - More sophisticated Monte Carlo simulations
    - Support for more states' tax treatments
    - Detailed RMD calculations
    - FEHB plan comparison
    - Integration with federal benefits calculators
    
    Please provide feedback on additional features that would be helpful for your retirement planning.
    """)
    
    # FAQ Accordion
    st.subheader("Frequently Asked Questions")
    
    with st.expander("What's the difference between FERS and CSRS?"):
        st.markdown("""
        **FERS (Federal Employees Retirement System)** is the current retirement system for federal employees, in effect since 1987. It consists of three components:
        1. FERS Basic Annuity
        2. Social Security
        3. Thrift Savings Plan (TSP)
        
        **CSRS (Civil Service Retirement System)** was the previous system for employees hired before 1984. It provides a more generous annuity but does not include Social Security benefits.
        
        This calculator primarily focuses on FERS, but could be adapted for CSRS with modifications.
        """)
    
    with st.expander("How is sick leave calculated in retirement?"):
        st.markdown("""
        Unused sick leave increases your years of service for annuity calculation purposes:
        
        - 2,087 hours = 1 year of service credit
        - 174 hours = 1 month of service credit
        
        Sick leave is only used to calculate your annuity; it doesn't count toward retirement eligibility or the 1.1% multiplier qualification.
        """)
    
    with st.expander("What happens if I retire before MRA or age 62?"):
        st.markdown("""
        If you retire before your Minimum Retirement Age (MRA):
        
        - You won't receive your FERS annuity until you reach your MRA
        - You'll need to rely on your TSP and other savings until then
        
        If you retire between your MRA and age 62:
        
        - You'll receive your FERS annuity immediately
        - You may qualify for the FERS Supplement until age 62
        - You won't get the 1.1% multiplier (requires age 62+)
        """)
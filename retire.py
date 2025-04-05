import streamlit as st
import pandas as pd
import datetime as dt
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="Retirement Scenario Explorer", layout="wide")

st.title("🧮 Federal Retirement Scenario Explorer")

# --- Input Sidebar ---
st.sidebar.header("Scenario A: Your Info")
birthdate_a = st.sidebar.date_input("Birthdate", dt.date(1965, 2, 25))
start_date_a = st.sidebar.date_input("Service Start Date", dt.date(1987, 6, 22))
retire_date_a = st.sidebar.date_input("Retirement Date", dt.date(2025, 8, 1))
high3_a = st.sidebar.number_input("High-3 Salary ($)", value=179000, step=1000)
tsp_balance_a = st.sidebar.number_input("TSP Balance ($)", value=1800000, step=10000)
social_security_age_a = st.sidebar.slider("Social Security Start Age", 62, 70, 67)
survivor_benefit_a = st.sidebar.selectbox("Survivor Benefit Option", ["None", "Partial", "Full"])
cola_a = st.sidebar.slider("Annual COLA (%)", 0.0, 0.04, 0.02)
tsp_growth_a = st.sidebar.slider("TSP Growth Rate (%)", 0.0, 0.10, 0.05)
tsp_withdraw_a = st.sidebar.slider("TSP Withdrawal Rate (%)", 0.0, 0.10, 0.04)
pa_resident_a = st.sidebar.checkbox("Pennsylvania Resident", value=True)

st.sidebar.markdown("---")
st.sidebar.header("Scenario B: Alternate or Spouse")
birthdate_b = st.sidebar.date_input("Birthdate (B)", dt.date(1967, 5, 10))
start_date_b = st.sidebar.date_input("Service Start Date (B)", dt.date(1990, 9, 15))
retire_date_b = st.sidebar.date_input("Retirement Date (B)", dt.date(2027, 7, 1))
high3_b = st.sidebar.number_input("High-3 Salary (B)", value=165000, step=1000)
tsp_balance_b = st.sidebar.number_input("TSP Balance (B)", value=1200000, step=10000)
social_security_age_b = st.sidebar.slider("Social Security Start Age (B)", 62, 70, 67)
survivor_benefit_b = st.sidebar.selectbox("Survivor Benefit Option (B)", ["None", "Partial", "Full"])
cola_b = st.sidebar.slider("Annual COLA (B) (%)", 0.0, 0.04, 0.02)
tsp_growth_b = st.sidebar.slider("TSP Growth Rate (B) (%)", 0.0, 0.10, 0.05)
tsp_withdraw_b = st.sidebar.slider("TSP Withdrawal Rate (B) (%)", 0.0, 0.10, 0.04)
pa_resident_b = st.sidebar.checkbox("Pennsylvania Resident (B)", value=True)

# --- Helper Function ---
def simulate_retirement(birthdate, start_date, retire_date, high3, tsp_start, ss_start_age,
                        survivor_option, cola, tsp_growth, tsp_withdraw, pa_resident):
    months = []
    fers = []
    tsp = []
    ss = []
    salary = []
    total = []

    age_62 = birthdate + relativedelta(years=62)
    ss_start_date = birthdate + relativedelta(years=ss_start_age)
    service_months = (retire_date.year - start_date.year) * 12 + retire_date.month - start_date.month
    service_years = service_months / 12
    multiplier = 0.011 if retire_date >= age_62 else 0.01

    survivor_reduction = {"None": 0.0, "Partial": 0.05, "Full": 0.10}[survivor_option]
    gross_annuity = multiplier * service_years * high3 * (1 - survivor_reduction)

    fed_tax = 0.22
    state_tax = 0.03 if not pa_resident else 0.00
    salary_tax = fed_tax + state_tax
    retirement_tax = fed_tax

    net_annuity = gross_annuity * (1 - retirement_tax)
    tsp_balance = tsp_start
    annuity_monthly = net_annuity / 12

    # Personalized SS estimate
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
    ss_base = ss_benefits_by_age.get(ss_start_age, 4012)
    ss_monthly = ss_base * (1 - retirement_tax)

    date = dt.date(2025, 1, 1)
    annuity_now = annuity_monthly

    for _ in range(26 * 12):
        if date < retire_date:
            s = (high3 * (1 - salary_tax)) / 12
            f = 0
            t = 0
        else:
            s = 0
            f = annuity_now
            tsp_draw = (tsp_balance * tsp_withdraw / 12) * (1 - retirement_tax)
            tsp_balance = (tsp_balance - (tsp_balance * tsp_withdraw / 12)) * (1 + tsp_growth / 12)
            t = tsp_draw
            if date.month == 1:
                annuity_now *= (1 + cola)

        ss_amt = ss_monthly if date >= ss_start_date else 0
        months.append(date)
        fers.append(f)
        tsp.append(t)
        ss.append(ss_amt)
        salary.append(s)
        total.append(f + t + ss_amt + s)

        date += relativedelta(months=1)

    return pd.DataFrame({
        "Date": months,
        "Salary": salary,
        "FERS": fers,
        "TSP": tsp,
        "Social Security": ss,
        "Total Income": total
    })

# --- Run Simulations ---
df_a = simulate_retirement(birthdate_a, start_date_a, retire_date_a, high3_a, tsp_balance_a,
                           social_security_age_a, survivor_benefit_a, cola_a,
                           tsp_growth_a, tsp_withdraw_a, pa_resident_a)

df_b = simulate_retirement(birthdate_b, start_date_b, retire_date_b, high3_b, tsp_balance_b,
                           social_security_age_b, survivor_benefit_b, cola_b,
                           tsp_growth_b, tsp_withdraw_b, pa_resident_b)

# --- Display ---
st.subheader("📈 Monthly Income Comparison")
st.line_chart(
    data=pd.DataFrame({
        "Scenario A": df_a["Total Income"].values,
        "Scenario B": df_b["Total Income"].values
    }, index=df_a["Date"])
)

# --- Combined Household View ---
st.subheader("👪 Combined Monthly Income")
df_combined = df_a.copy()
df_combined["Combined Total"] = df_a["Total Income"] + df_b["Total Income"]
st.line_chart(data=df_combined.set_index("Date")["Combined Total"])

# --- Show Data Table ---
with st.expander("📋 View Raw Tables"):
    st.write("Scenario A")
    st.dataframe(df_a)
    st.write("Scenario B")
    st.dataframe(df_b)
    st.write("Combined")
    st.dataframe(df_combined)

# --- Footer ---
st.caption("Built with ❤️ using Streamlit. Future-ready for OpenAI integration 🚀")
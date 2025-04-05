# Federal Retirement Calculator - Setup Guide

## Project Structure

Your retirement calculator is now modularized and ready to use. Here's how the files are organized:

```
federal-retirement-explorer/
├── streamlit_app.py       # Main UI entry point
├── ui_components.py       # UI components and rendering functions
├── retirement_model.py    # Core calculation engine
├── scenario_manager.py    # Scenario saving/loading
├── plots.py               # Visualization functions
├── monte_carlo.py         # Risk analysis
├── main.py                # Launcher script
├── requirements.txt       # Dependencies
└── scenarios/             # Saved scenario files (created on first save)
```

## Running the Application

1. First, install the dependencies:
```
pip install -r requirements.txt
```

2. Run the application either through the launcher:
```
python main.py
```

Or directly with streamlit:
```
streamlit run streamlit_app.py
```

3. The application will open in your web browser at http://localhost:8501

## Customization Options

### Add New Features

To add new features or capabilities:

1. **Add UI components**: Modify `ui_components.py` to add new input fields or displays
2. **Enhance calculations**: Extend `retirement_model.py` with new financial formulas
3. **Add visualizations**: Create new chart functions in `plots.py`

### Monte Carlo Simulation Configuration

The Monte Carlo simulation has several parameters you can adjust:

- **COLA variability**: Controls inflation uncertainty
- **TSP growth variability**: Controls market return uncertainty
- **Number of simulations**: More simulations = more accurate results but slower

## Data Management

- **Saving scenarios**: Enter a name and click "Save Scenario"
- **Loading scenarios**: Select from the dropdown at the top of each scenario panel
- **Exporting data**: Use the "Export Data" section to download Excel files
- **Backup all scenarios**: Use "Export All Saved Scenarios" in the Settings tab

## Troubleshooting

If you encounter any issues:

1. **Dependency errors**: Ensure you've installed all required packages
   ```
   pip install -r requirements.txt
   ```

2. **File not found errors**: Make sure all Python files are in the same directory

3. **Data persistence issues**: Check if the "scenarios" directory exists and has write permissions

4. **Plot rendering issues**: Try falling back to Matplotlib if Plotly isn't working
   ```
   pip install matplotlib
   ```

Enjoy exploring your federal retirement options!
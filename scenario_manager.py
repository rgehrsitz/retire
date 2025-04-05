import os
import json
import datetime as dt

def save_scenario(scenario_data, scenario_name):
    """Save scenario to a JSON file"""
    # Convert dates to string format
    scenario_data_copy = scenario_data.copy()
    for key in scenario_data_copy:
        if isinstance(scenario_data_copy[key], dt.date):
            scenario_data_copy[key] = scenario_data_copy[key].strftime('%Y-%m-%d')
    
    # Save to file
    os.makedirs("scenarios", exist_ok=True)
    with open(f"scenarios/{scenario_name}.json", "w") as f:
        json.dump(scenario_data_copy, f)
    
    return f"Scenario saved as 'scenarios/{scenario_name}.json'"

def load_scenario(scenario_file):
    """Load scenario from a JSON file"""
    with open(scenario_file, "r") as f:
        scenario_data = json.load(f)
    
    # Convert date strings back to date objects
    for key in ['birthdate', 'start_date', 'retire_date']:
        if key in scenario_data:
            scenario_data[key] = dt.datetime.strptime(scenario_data[key], '%Y-%m-%d').date()
    
    return scenario_data

def get_available_scenarios():
    """Get list of available saved scenarios"""
    if not os.path.exists("scenarios"):
        return []
    
    return [f.replace(".json", "") for f in os.listdir("scenarios") if f.endswith(".json")]

def delete_scenario(scenario_name):
    """Delete a saved scenario"""
    scenario_path = f"scenarios/{scenario_name}.json"
    if os.path.exists(scenario_path):
        os.remove(scenario_path)
        return True
    return False

def export_all_scenarios():
    """Export all scenarios as a zip file"""
    import zipfile
    import io
    
    if not os.path.exists("scenarios") or not os.listdir("scenarios"):
        return None
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for scenario_file in os.listdir("scenarios"):
            if scenario_file.endswith(".json"):
                zipf.write(os.path.join("scenarios", scenario_file), scenario_file)
    
    return zip_buffer.getvalue()

def import_scenarios(zip_file):
    """Import scenarios from a zip file"""
    import zipfile
    import io
    
    os.makedirs("scenarios", exist_ok=True)
    
    with zipfile.ZipFile(io.BytesIO(zip_file), "r") as zipf:
        for file_name in zipf.namelist():
            if file_name.endswith(".json"):
                zipf.extract(file_name, "scenarios")
    
    return len([f for f in zipf.namelist() if f.endswith(".json")])

def clear_all_scenarios():
    """Delete all saved scenarios"""
    if os.path.exists("scenarios"):
        import shutil
        shutil.rmtree("scenarios")
        return True
    return False
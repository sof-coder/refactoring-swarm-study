import os
import json
import csv
from datetime import datetime, timedelta

# --- CONFIGURATION ---
JSON_FOLDER = "./Experiment_data_files"  # Folder containing JSON files
OUTPUT_FILE = "./results/team_grades_out_of_20.csv"

# The exact time slot of the Google Meet
MEET_START = datetime.strptime("2026-02-28 22:20:00", "%Y-%m-%d %H:%M:%S")
MEET_END = datetime.strptime("2026-02-28 23:59:00", "%Y-%m-%d %H:%M:%S")

# The EXACT names of the 3 files from the hidden_dataset
EXPECTED_FILES = ["bad_syntax.py", "logic_bug.py", "messy_code.py"]

def evaluate_timing(start_time):
    """Evaluates the execution timing proximity to the Meet time slot (out of 2 pts)."""
    if MEET_START <= start_time <= MEET_END:
        return 2, "✅ Perfect timing"
    
    if start_time < MEET_START:
        distance = MEET_START - start_time
    else:
        distance = start_time - MEET_END
        
    if distance <= timedelta(minutes=30):
        return 1, "⚠️ Slight delay (< 30 min)"
    else:
        return 0, "❌ Execution outside the time window (Different time)"

def create_empty_row(team_name, note):
    """Generates a default row for inconsistent files (0 everywhere)."""
    return {
        "Team_Name": team_name,
        "Start_Date": "N/A",
        "End_Date": "N/A",
        "Nb_Agents": 0,
        "Agents_List": "N/A",
        "Total_Calls": 0,
        "API_Errors": 0,
        "Files_Processed": "N/A",
        "Timing_Pts_2": 0,
        "Agents_Pts_6": 0,
        "API_Pts_4": 0,
        "Volume_Pts_2": 0,
        "Files_Processed_6": 0,
        "Team_Score_20": 0,
        "Notes": note
    }

def evaluate_team(file_path):
    team_name = os.path.basename(file_path).replace("_experiment_data.json", "")
    
    try:
        # 1. Basic checks (Structure)
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                return create_empty_row(team_name, "❌ INCONSISTENCY: Corrupted or malformed JSON file.")
                
        if not logs:
            return create_empty_row(team_name, "❌ INCONSISTENCY: The file is empty.")
            
        if not isinstance(logs, list):
            return create_empty_row(team_name, "❌ STRUCTURAL INCONSISTENCY: The JSON is not a list.")
            
        if not all(isinstance(log, dict) for log in logs):
            return create_empty_row(team_name, "❌ STRUCTURAL INCONSISTENCY: Invalid elements in the list.")

        # --- FILE SEARCH ---
        full_json_content = json.dumps(logs)
        found_files = [f for f in EXPECTED_FILES if f in full_json_content]
        found_files_count = len(found_files)

        # --- BASIC METRICS ---
        total_calls = len(logs)
        used_agents = set(log.get('agent', 'Unknown') for log in logs)
        api_errors = sum(1 for log in logs if log.get('status') != 'SUCCESS')
        successful_calls = total_calls - api_errors
        
        # --- TIMESTAMPING ---
        try:
            start_str = logs[0].get('timestamp')
            end_str = logs[-1].get('timestamp')
            
            if not start_str or not end_str:
                return create_empty_row(team_name, "❌ INCONSISTENCY: 'timestamp' key missing.")
                
            start_str = start_str.replace('Z', '')[:19]
            end_str = end_str.replace('Z', '')[:19]
            
            start_time = datetime.fromisoformat(start_str)
            end_time = datetime.fromisoformat(end_str)
        except ValueError:
            return create_empty_row(team_name, "❌ FORMAT INCONSISTENCY: Invalid date format.")
        
        # ==========================================
        # DETAILED SCORING CALCULATION
        # ==========================================
        details = []
        
        # Criterion 1: Timing (out of 2 pts)
        pts_timing, msg_timing = evaluate_timing(start_time)
        details.append(msg_timing)
        
        # Criterion 2: Agents (out of 6 pts)
        nb_agents = len(used_agents)
        if nb_agents >= 3:
            pts_agents = 6
        elif nb_agents == 2:
            pts_agents = 3
            details.append("⚠️ Only 2 agents used")
        else:
            pts_agents = 0
            details.append("❌ Only 1 agent used (No Swarm)")
            
        # Criterion 3: API Errors (out of 4 pts)
        if api_errors <= 2:
            pts_api = 4
        elif api_errors <= 5:
            pts_api = 2
            details.append(f"⚠️ {api_errors} API errors")
        else:
            pts_api = 0
            details.append(f"❌ Many API errors ({api_errors})")
            
        # Criterion 4: Call volume (out of 2 pts)
        if successful_calls >= 3:
            pts_volume = 2
        else:
            pts_volume = 0
            details.append("❌ Less than 3 successful calls")

        # Criterion 5: Expected files (out of 6 pts)
        # if found_files_count == len(EXPECTED_FILES):
        #     files_text = f"{found_files_count}/{len(EXPECTED_FILES)} processed"
        #     files_points = found_files_count *
        # elif

        files_points = 0
        if found_files_count == 0:
            files_text = "No files processed"
            files_points = 0
            details.append("❌ NO files from hidden_dataset processed (0 pts)")
        else:
            files_text = f"{found_files_count}/{len(EXPECTED_FILES)} processed ({','.join(found_files)})"
            files_points = found_files_count * 2  # 2 pts per file found
            details.append(f"⚠️ Missing files ({(len(EXPECTED_FILES) - found_files_count) })")
            
        # --- FINAL SCORE ---
        final_score = pts_timing + pts_agents + pts_api + pts_volume + files_points
        final_score = max(0, final_score) # Prevent negative scores
            
        return {
            "Team_Name": team_name,
            "Start_Date": start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "End_Date": end_time.strftime('%Y-%m-%d %H:%M:%S'),
            "Nb_Agents": nb_agents,
            "Agents_List": " | ".join(used_agents),
            "Total_Calls": total_calls,
            "API_Errors": api_errors,
            "Files_Processed": files_text,
            "Timing_Pts_2": pts_timing,
            "Agents_Pts_6": pts_agents,
            "API_Pts_4": pts_api,
            "Volume_Pts_2": pts_volume,
            "Files_Processed_6": files_points,
            "Team_Score_20": final_score,
            "Notes": " - ".join(details)
        }
        
    except Exception as e:
        return create_empty_row(team_name, f"❌ SYSTEM ERROR: {str(e)}")

# --- MAIN PROGRAM ---
print("🔍 Starting intelligent log evaluation with scoring details...\n")
results = []

found_files_main = [f for f in os.listdir(JSON_FOLDER) if f.endswith("_experiment_data.json")]

if not found_files_main:
    print("⚠️ No JSON files found in the current folder.")
else:
    for json_file in found_files_main:
        path = os.path.join(JSON_FOLDER, json_file)
        results.append(evaluate_team(path))
    
    
    # New fields with point details
    fieldnames = [
        "Team_Name", "Start_Date", "End_Date", "Nb_Agents", "Agents_List", "Total_Calls", "API_Errors",
        "Files_Processed", "Timing_Pts_2", "Agents_Pts_6", "API_Pts_4", "Volume_Pts_2",
        "Files_Processed_6", "Team_Score_20", "Notes"
    ]

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"✅ Analysis completed on {len(found_files_main)} files! Detailed results are in '{OUTPUT_FILE}'")
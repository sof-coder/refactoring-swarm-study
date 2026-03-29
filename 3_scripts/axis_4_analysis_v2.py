import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import ast
import os
import zipfile
from scipy import stats

# --- CONFIGURATION ---
# Input Files for the report and analysis
ZIP_HISTORY = "../2_data/history_experiment_data.zip"
ZIP_HACKATHON = "../2_data/hacktown_experiment_data.zip"
GLOBAL_STUDENT_EVALUATION_FILE = '../2_data/global_student_evaluation.csv'
DATA_TEAM_FILE = '../2_data/en_data_teams.csv'
# Output directory for the report and the high-resolution plots
RESULTS_DIR = "../4_results/research_results_axis_4"
os.makedirs(RESULTS_DIR, exist_ok=True)

# Visual style setup for academic publication
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.2)

print("🚀 Starting Master Axis 4 Analysis (Prototyping and Hackathon Logs)...")

# --- 1. LOAD CSV DATA (SCORES & LLMs) ---

df_students = pd.read_csv(GLOBAL_STUDENT_EVALUATION_FILE, sep=';')

df_teams = pd.read_csv(DATA_TEAM_FILE)

df_students['team_clean'] = df_students['Team_name'].astype(str).str.strip().str.lower()
team_col_name = 'TeamName' if 'TeamName' in df_teams.columns else 'Equipe'
df_teams['team_clean'] = df_teams[team_col_name].astype(str).str.strip().str.lower()

df_team_info = pd.merge(df_students, df_teams[['team_clean', 'LLM']], on='team_clean', how='left')
df_team_info = df_team_info.groupby('team_clean').first().reset_index()

def categorize_llm(name):
    name = str(name).lower()
    if 'gemini' in name: return 'Gemini'
    if 'mistral' in name or 'mixtral' in name: return 'Mistral'
    if 'llama' in name: return 'Llama'
    return 'Other'

df_team_info['llm_family'] = df_team_info['LLM'].apply(categorize_llm)

# --- 2. ZIP EXTRACTION FUNCTION ---
def extract_prompt_length(details):
    try:
        if isinstance(details, dict): return len(str(details.get('input_prompt', '')))
        if isinstance(details, str):
            try:
                parsed = json.loads(details)
                if isinstance(parsed, dict): return len(str(parsed.get('input_prompt', '')))
            except json.JSONDecodeError:
                try:
                    parsed_ast = ast.literal_eval(details)
                    if isinstance(parsed_ast, dict): return len(str(parsed_ast.get('input_prompt', '')))
                except (ValueError, SyntaxError): pass
    except Exception: pass
    return 0

def standardize_agent(name):
    name = str(name).lower()
    if 'audit' in name: return 'Auditor'
    if 'fix' in name: return 'Fixer'
    if 'judg' in name or 'test' in name: return 'Judge'
    if 'orchest' in name: return 'Orchestrator'
    return 'Other'

def process_zip_logs(zip_path, phase_name):
    """Reads JSON files directly from a ZIP archive and returns a DataFrame."""
    print(f"📦 Extracting {phase_name} logs directly from '{zip_path}'...")
    all_logs = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            json_files = [f for f in z.namelist() if f.endswith('.json')]
            for filename in json_files:
                team_name_raw = os.path.basename(filename).replace('_experiment_data.json', '').replace('_experiment_data_historique.json', '')
                team_name = team_name_raw.strip().lower()
                try:
                    with z.open(filename) as f:
                        team_data = json.loads(f.read().decode('utf-8'))
                        for log in team_data:
                            if log.get('agent') == 'System': continue
                            all_logs.append({
                                'team_clean': team_name,
                                'phase': phase_name,
                                'timestamp': log.get('timestamp'),
                                'std_agent': standardize_agent(log.get('agent')),
                                'action': log.get('action'),
                                'status': log.get('status'),
                                'prompt_length': extract_prompt_length(log.get('details'))
                            })
                except Exception: pass
    except FileNotFoundError:
        print(f"⚠️ Warning: '{zip_path}' not found.")
        return pd.DataFrame()
    
    df = pd.DataFrame(all_logs)
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.sort_values(by=['team_clean', 'timestamp']).reset_index(drop=True)
    return df

# Extract both ZIP files and create DataFrames for Prototyping and Hackathon logs
df_prototyping = process_zip_logs(ZIP_HISTORY, 'Prototyping')
df_hackathon = process_zip_logs(ZIP_HACKATHON, 'Hackathon')

# --- 3. COMPUTE BEHAVIORAL METRICS ---
print("⚙️ Computing behavioral metrics (Prototyping Volume & Hackathon Loops)...")

# Metric 1: Prototyping Volume (From History Logs)
if not df_prototyping.empty:
    prototyping_volume = df_prototyping.groupby('team_clean').agg(
        dev_api_calls=('std_agent', 'count')
    ).reset_index()
    df_team_info = pd.merge(df_team_info, prototyping_volume, on='team_clean', how='left').fillna({'dev_api_calls': 0})

# Metric 2: Hackathon Behavior
if not df_hackathon.empty:
    df_hackathon['next_agent'] = df_hackathon.groupby('team_clean')['std_agent'].shift(-1)
    df_hackathon['is_tdd_loop'] = (df_hackathon['std_agent'] == 'Fixer') & (df_hackathon['next_agent'] == 'Judge')
    
    hackathon_behavior = df_hackathon.groupby('team_clean').agg(
        hackathon_api_calls=('std_agent', 'count'),
        avg_prompt_length=('prompt_length', lambda x: x[x > 10].mean()),
        tdd_loops_count=('is_tdd_loop', 'sum')
    ).reset_index()
    
    df_final = pd.merge(df_team_info, hackathon_behavior, on='team_clean', how='inner')
else:
    df_final = df_team_info

# --- 4. VISUALIZATIONS & REPORT GENERATION ---
print("📊 Generating Axis 4 plots and statistical report...")

with open(f"{RESULTS_DIR}/Deep_Axis4_Combined_Report.txt", "w", encoding='utf-8') as report:
    report.write("=== DEEP AXIS 4: BEHAVIORAL REPORT (PROTOTYPING + HACKATHON) ===\n\n")
    report.write(f"Total API Calls Processed (Prototyping Phase): {len(df_prototyping)}\n")
    report.write(f"Total API Calls Processed (Hackathon Phase): {len(df_hackathon)}\n\n")

    if not df_prototyping.empty and 'dev_api_calls' in df_final.columns:
        corr_dev, p_dev = stats.pearsonr(df_final['dev_api_calls'].fillna(0), df_final['Team_Score_20'].fillna(0))
        report.write(f"Correlation [Prototyping API Calls] vs [Team Score]: {corr_dev:.2f} (p-value: {p_dev:.4f})\n")
        
        plt.figure(figsize=(8, 6))
        sns.regplot(data=df_final, x='dev_api_calls', y='Team_Score_20', scatter_kws={'alpha': 0.6}, line_kws={'color': 'orange'})
        plt.title("Axis 4: The Development Paradox (Prototyping Calls vs Final Score)")
        plt.xlabel("Total API Calls during Asynchronous Prototyping Phase")
        plt.ylabel("Final Team Score (/20)")
        plt.tight_layout()
        plt.savefig(f"{RESULTS_DIR}/Axis4_Development_Paradox.png", dpi=300)
        plt.close()

    if not df_hackathon.empty:
        corr_tdd, p_tdd = stats.pearsonr(df_final['tdd_loops_count'].fillna(0), df_final['Team_Score_20'].fillna(0))
        report.write(f"Correlation [Hackathon TDD Loops] vs [Team Score]: {corr_tdd:.2f} (p-value: {p_tdd:.4f})\n\n")

        plt.figure(figsize=(8, 6))
        sns.regplot(data=df_final, x='tdd_loops_count', y='Team_Score_20', scatter_kws={'alpha': 0.6}, line_kws={'color': 'red'})
        plt.title("Axis 4: Impact of Test-Driven Development (Fixer->Judge Loops)")
        plt.xlabel("Number of TDD Loops Executed during Hackathon")
        plt.ylabel("Final Team Score (/20)")
        plt.tight_layout()
        plt.savefig(f"{RESULTS_DIR}/Axis4_TDD_vs_Score.png", dpi=300)
        plt.close()

        df_major_llms = df_final[df_final['llm_family'].isin(['Gemini', 'Mistral', 'Llama'])]
        plt.figure(figsize=(8, 5))
        sns.boxplot(data=df_major_llms, x='llm_family', y='avg_prompt_length', palette='Set2')
        plt.title("Axis 4: Prompt Context Size Engineering by LLM Family")
        plt.xlabel("LLM Family")
        plt.ylabel("Average Prompt Length (Characters)")
        plt.yscale("log")
        plt.tight_layout()
        plt.savefig(f"{RESULTS_DIR}/Axis4_Prompt_Size_by_LLM.png", dpi=300)
        plt.close()

        df_transitions = df_hackathon.dropna(subset=['next_agent'])
        df_transitions = df_transitions[(df_transitions['std_agent'] != 'Other') & (df_transitions['next_agent'] != 'Other')]
        transition_matrix = pd.crosstab(df_transitions['std_agent'], df_transitions['next_agent'])
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(transition_matrix, annot=True, fmt='d', cmap='YlGnBu', cbar_kws={'label': 'Transition Count'})
        plt.title("Axis 4: Global Swarm Agent Transitions (Hackathon)")
        plt.xlabel("Target Agent (Called)")
        plt.ylabel("Source Agent (Caller)")
        plt.tight_layout()
        plt.savefig(f"{RESULTS_DIR}/Axis4_Global_Transitions_Heatmap.png", dpi=300)
        plt.close()
        
        report.write("--- Top 5 Most Frequent Hackathon Transitions ---\n")
        top_trans = df_transitions.groupby(['std_agent', 'next_agent']).size().sort_values(ascending=False).head(5)
        report.write(top_trans.to_string() + "\n\n")

print(f"✅ Master Axis 4 analysis complete! Check '{RESULTS_DIR}' for the plots and the combined report.")

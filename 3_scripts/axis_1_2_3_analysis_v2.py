import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os

# --- CONFIGURATION ---
# Input Files for the report and analysis
GLOBAL_STUDENT_EVALUATION_FILE = '../2_data/global_student_evaluation.csv'
DATA_TEAM_FILE = '../2_data/en_data_teams.csv'
# Output directory for the report and the high-resolution plots
RESULTS_DIR = "../4_results/research_results_axis_1_2_3"
os.makedirs(RESULTS_DIR, exist_ok=True)

# Visual style setup for academic publication
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.2)

print("📊 Starting full deep analysis and generating all artifacts...")

# --- 1. DATA LOADING & CLEANING ---
df_students = pd.read_csv(GLOBAL_STUDENT_EVALUATION_FILE, sep=';')
df_teams = pd.read_csv(DATA_TEAM_FILE)

# Standardize team names for robust merging
df_students['team_clean'] = df_students['Team_name'].astype(str).str.strip().str.lower()
team_col_name = 'TeamName' if 'TeamName' in df_teams.columns else 'Equipe'
df_teams['team_clean'] = df_teams[team_col_name].astype(str).str.strip().str.lower()

# Merge datasets
df_merged = pd.merge(df_students, df_teams[['team_clean', 'LLM']], on='team_clean', how='left')
team_data = df_merged.groupby('team_clean').first().reset_index()

# --- 2. STATISTICAL ANALYSIS & REPORT GENERATION ---
with open(f"{RESULTS_DIR}/Deep_Analysis_Report.txt", "w", encoding='utf-8') as report:
    report.write("=== DEEP V2 STATISTICAL ANALYSIS REPORT ===\n\n")

    # ==========================================
    # --- AXIS 1: LLM PARITY ANALYSIS ---
    # ==========================================
    report.write("--- AXIS 1 : LLM PERFORMANCE (REPRESENTATIVE SAMPLES ONLY) ---\n")
    
    def categorize_llm(name):
        name = str(name).lower()
        if 'gemini' in name: return 'Gemini'
        if 'mistral' in name or 'mixtral' in name: return 'Mistral'
        if 'llama' in name: return 'Llama'
        if 'claude' in name: return 'Claude'
        if 'gemma' in name: return 'Gemma'
        return 'Other (Non-Representative)'

    team_data['llm_family'] = team_data['LLM'].apply(categorize_llm)
    
    # Filter out models used by fewer than 5 teams
    llm_counts = team_data['llm_family'].value_counts()
    major_llms = llm_counts[llm_counts >= 5].index.tolist()
    df_major_llms = team_data[team_data['llm_family'].isin(major_llms)]
    
    # Write stats to report
    res_axis1 = df_major_llms.groupby('llm_family').agg(
        team_count=('Team_Score_20', 'count'),
        avg_score=('Team_Score_20', 'mean'),
        std_deviation=('Team_Score_20', 'std')
    ).round(2)
    report.write("Performance of statistically significant LLM families (N >= 5):\n")
    report.write(res_axis1.to_string() + "\n")
    
    # ANOVA Test
    anova_groups = [df_major_llms[df_major_llms['llm_family'] == llm]['Team_Score_20'].dropna() for llm in major_llms]
    f_stat, p_anova = stats.f_oneway(*anova_groups)
    report.write(f"\n[Statistical Test] ANOVA p-value across major LLMs: {p_anova:.4f}\n")
    if p_anova > 0.05:
        report.write("-> Conclusion: NO significant difference. The models have reached parity.\n\n")

    # Plot 1.1: Violin Plot (Score Distribution)
    plt.figure(figsize=(10, 6))
    sns.violinplot(data=df_major_llms, x='llm_family', y='Team_Score_20', inner="quartile")
    plt.title("Axis 1: Density & Distribution of Scores by Major LLMs")
    plt.tight_layout()
    plt.savefig(f"{RESULTS_DIR}/Deep_Axis1_Violin.png", dpi=300)
    plt.close()

    # Plot 1.2: Bar Plot (API Errors)
    plt.figure(figsize=(8, 5))
    sns.barplot(data=df_major_llms, x='llm_family', y='API_Errors', capsize=.1, errorbar=('ci', 95), palette='Blues_d')
    plt.title("Axis 1: Average API Errors by Major LLM Family")
    plt.ylabel("Average API Errors (Lower is better)")
    plt.xlabel("LLM Family")
    plt.tight_layout()
    plt.savefig(f"{RESULTS_DIR}/Extra_Axis1_API_Errors.png", dpi=300)
    plt.close()

    # ==========================================
    # --- AXIS 2: EXPERTISE (QUARTILE T-TEST) ---
    # ==========================================
    report.write("--- AXIS 2 : PYTHON EXPERTISE OVERALL IMPACT ---\n")
    
    # Calculate average Python level per team
    team_data['avg_python_level'] = df_merged.groupby('team_clean')['Python_Level'].transform('mean')
    
    q75_py = team_data['avg_python_level'].quantile(0.75)
    q25_py = team_data['avg_python_level'].quantile(0.25)
    
    top_python_teams = team_data[team_data['avg_python_level'] >= q75_py]['Team_Score_20'].dropna()
    bot_python_teams = team_data[team_data['avg_python_level'] <= q25_py]['Team_Score_20'].dropna()
    
    # T-Test
    t_stat_py, p_ttest_py = stats.ttest_ind(top_python_teams, bot_python_teams)
    
    report.write(f"Top 25% Python Teams Avg Score: {top_python_teams.mean():.2f} / 20\n")
    report.write(f"Bottom 25% Python Teams Avg Score: {bot_python_teams.mean():.2f} / 20\n")
    report.write(f"[Statistical Test] Independent T-test p-value: {p_ttest_py:.4f}\n\n")

    # Plot 2: Boxplot (Expertise Extremes)
    def categorize_expertise(val):
        if pd.isna(val): return "Unknown"
        if val >= q75_py: return "Top 25% (Experts)"
        if val <= q25_py: return "Bottom 25% (Beginners)"
        return "Average"

    team_data['expertise_group'] = team_data['avg_python_level'].apply(categorize_expertise)
    df_expertise_extremes = team_data[team_data['expertise_group'].isin(["Top 25% (Experts)", "Bottom 25% (Beginners)"])]

    plt.figure(figsize=(8, 5))
    sns.boxplot(data=df_expertise_extremes, x='expertise_group', y='Team_Score_20', palette='Set2')
    plt.title("Axis 2: Final Score vs Initial Python Expertise (The AI Equalizer Effect)")
    plt.ylabel("Final AI Swarm Score (/20)")
    plt.xlabel("Team's Average Python Level")
    plt.tight_layout()
    plt.savefig(f"{RESULTS_DIR}/Extra_Axis2_Expertise_Boxplot.png", dpi=300)
    plt.close()

    # ==========================================
    # --- AXIS 3: TEAM DYNAMICS (QUARTILE T-TEST) ---
    # ==========================================
    report.write("--- AXIS 3 : TEAM COLLABORATION IMPACT ---\n")
    
    q75_bal = team_data['Git_Work_Balance_Pts_10'].quantile(0.75)
    q25_bal = team_data['Git_Work_Balance_Pts_10'].quantile(0.25)
    
    highly_balanced = team_data[team_data['Git_Work_Balance_Pts_10'] >= q75_bal]['Team_Score_20'].dropna()
    poorly_balanced = team_data[team_data['Git_Work_Balance_Pts_10'] <= q25_bal]['Team_Score_20'].dropna()
    
    # T-Test
    t_stat_bal, p_ttest_bal = stats.ttest_ind(highly_balanced, poorly_balanced)
    
    report.write(f"Top 25% Most Balanced Teams Avg Score: {highly_balanced.mean():.2f} / 20\n")
    report.write(f"Bottom 25% Least Balanced Teams (Lone Wolves) Avg Score: {poorly_balanced.mean():.2f} / 20\n")
    report.write(f"[Statistical Test] Independent T-test p-value: {p_ttest_bal:.4f}\n")
    if p_ttest_bal > 0.05:
        report.write("-> Conclusion: While balanced teams perform slightly better, the gap is NOT statistically significant.\n")

    # Plot 3: Regression Plot (Dynamics)
    plt.figure(figsize=(8, 6))
    sns.regplot(data=team_data, x='Git_Work_Balance_Pts_10', y='Team_Score_20', 
                scatter_kws={'alpha': 0.6, 's': 50}, line_kws={'color': 'red', 'lw': 2})
    plt.title("Axis 3: Team Collaboration vs AI Performance")
    plt.xlabel("Git Work Balance Score (0 = Lone Wolf, 10 = Perfect Harmony)")
    plt.ylabel("Final AI Swarm Score (/20)")
    plt.xlim(-0.5, 10.5)
    plt.tight_layout()
    plt.savefig(f"{RESULTS_DIR}/Extra_Axis3_Dynamics_Regplot.png", dpi=300)
    plt.close()

print("✅ Success! The report and all 4 high-resolution plots have been generated in 'research_results_deep_v2'.")

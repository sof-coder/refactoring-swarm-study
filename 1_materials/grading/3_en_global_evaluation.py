import pandas as pd
import os

def main():
    INPUT_INDIVIDUAL_GRADE_FILE = './results/individual_grades_out_of_20.csv'
    INPUT_TEAMS_GRADE_FILE = './results/team_grades_out_of_20.csv'
    OUTPUT_STUDENT_GLOBAL_EVALUATION = './results/global_student_evaluation.csv'

    if not os.path.exists(INPUT_INDIVIDUAL_GRADE_FILE):
        print(f"❌ Error: {INPUT_INDIVIDUAL_GRADE_FILE} not found.")
        return
    if not os.path.exists(INPUT_TEAMS_GRADE_FILE):
        print(f"❌ Error: {INPUT_TEAMS_GRADE_FILE} not found.")
        return

    print("📄 Loading CSV files...")
    # Load the datasets with their respective separators
    df_individual = pd.read_csv(INPUT_INDIVIDUAL_GRADE_FILE, sep=';')
    df_team = pd.read_csv(INPUT_TEAMS_GRADE_FILE, sep=',')

    # Identify the team name column in the individual dataframe
    # It might be 'Team_name_x', 'Team_name', or 'Team_Name'
    team_col_indiv = None
    for col in ['Team_name_x', 'Team_name', 'Team_Name']:
        if col in df_individual.columns:
            team_col_indiv = col
            break
            
    if team_col_indiv is None:
        print("❌ Error: Could not find the team name column in individual grades.")
        return

    # Identify the team name column in the team dataframe
    team_col_team = None
    for col in ['Team_Name', 'Team_name', 'team_name']:
        if col in df_team.columns:
            team_col_team = col
            break

    if team_col_team is None:
        print("❌ Error: Could not find the team name column in team grades.")
        return

    print("🔗 Normalized team names for accurate joining...")
    # Create normalized keys for joining to handle spaces and case differences
    df_individual['join_key'] = df_individual[team_col_indiv].astype(str).str.strip().str.lower()
    df_team['join_key'] = df_team[team_col_team].astype(str).str.strip().str.lower()

    # Merge the two dataframes on the normalized key
    df_merged = pd.merge(df_individual, df_team, on='join_key', how='left')

    # Drop the temporary join key
    df_merged.drop(columns=['join_key'], inplace=True)
    
    # Ensure only Team_name column exists (remove Team_Name)
    if 'Team_Name' in df_merged.columns and 'Team_name' in df_merged.columns:
        df_merged.drop(columns=['Team_Name'], inplace=True)
    elif 'Team_Name' in df_merged.columns:
        df_merged.rename(columns={'Team_Name': 'Team_name'}, inplace=True)

    # Calculate average score
    # Ensure both scores are numeric
    df_merged['Participation_Score'] = pd.to_numeric(df_merged['Participation_Score'], errors='coerce').fillna(0)
    df_merged['Team_Score_20'] = pd.to_numeric(df_merged['Team_Score_20'], errors='coerce').fillna(0)
    
    # Calculate the mean of Participation_Score and Team_Score_20
    df_merged['Global_Score_20'] = (df_merged['Participation_Score'] + df_merged['Team_Score_20']) / 2

    print("📊 Calculating final scores (Average of Participation and Team scores)...")
    
    # Save the result to a new CSV file
    df_merged.to_csv(OUTPUT_STUDENT_GLOBAL_EVALUATION, index=False, sep=';')
    
    print(f"✅ Success! Merged data saved to {OUTPUT_STUDENT_GLOBAL_EVALUATION}")
    
if __name__ == "__main__":
    main()

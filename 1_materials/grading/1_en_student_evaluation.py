import pandas as pd
import csv
import requests
import re
import time
import sys
import os

# --- CONFIGURATION ---
GITHUB_TOKEN = "YOUR GITHUB ACCESS TOKEN HERE"
INPUT_TEAM_FILE = "en_data_teams.csv"
INPUT_STUDENTS_PROFILE_FILE = 'students_profile_anonymized.csv'
OUTPUT_GITHUB_CONTRIBUTION_DATA = "./results/github_contribution_data.csv"
ENRICHED_OUTPUT_FILE = './results/individual_grades_out_of_20.csv'
UNPROCESSED_FILE = "unprocessed_team.csv"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def extract_owner_repo(url):
    """Extracts the username and repository name from the GitHub URL."""
    match = re.search(r"github\.com/([^/]+)/([^/.]+)", url)
    if match:
        return match.groups()
    return None, None

def get_local_identities(owner, repo):
    """
    Retrieves the commit history to extract the real names and emails
    configured on the students' computers.
    """
    # Get the last 100 commits (sufficient for a practical assignment)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=100"
    try:
        response = requests.get(api_url, headers=HEADERS, timeout=10)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        print(f"   ⚠️ Timeout/Connection error fetching commits: {e}")
        return {}

    identity_mapping = {}

    if response.status_code == 200:
        for commit_data in response.json():
            # Raw identity left by the student's computer
            raw_name = commit_data['commit']['author']['name']
            raw_email = commit_data['commit']['author']['email']
            local_identity = f"{raw_name} ({raw_email})"

            # GitHub account identity (if it exists)
            gh_user = commit_data.get('author')
            gh_login = gh_user['login'] if gh_user else "Account_Not_Configured"

            if gh_login not in identity_mapping:
                identity_mapping[gh_login] = set()
            identity_mapping[gh_login].add(local_identity)

    # Convert sets to readable strings
    return {login: " | ".join(identities) for login, identities in identity_mapping.items()}

def get_contributor_stats(owner, repo, team_name="", link=""):
    """Calls the GitHub API to get code statistics (added/deleted lines)."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/stats/contributors"

    max_attempts = 5
    attempt = 0
    response = None

    # Retry loop if GitHub returns 202
    while attempt < max_attempts:
        try:
            response = requests.get(api_url, headers=HEADERS, timeout=10)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"   ⚠️ Timeout/Connection error (attempt {attempt + 1}/{max_attempts}): {type(e).__name__}")
            time.sleep(5)
            attempt += 1
            continue

        if response.status_code == 202:
            print(f"   ⏳ GitHub is calculating stats ({attempt + 1}/{max_attempts}), please wait 5s...")
            time.sleep(5) # Give GitHub 5 seconds to compute
            attempt += 1
        else:
            break # If we get 200 (Success) or 404 (Not found), exit the loop

    if response is None or response.status_code != 200:
        error_code = response.status_code if response else "TIMEOUT"
        print(f"❌ Error {error_code} for {owner}/{repo}")
        return []

    data = response.json()
    team_stats = []
    total_team_commits = 0

    # 1. Retrieve the real email addresses in parallel
    local_identities = get_local_identities(owner, repo)

    # 2. Process the statistics
    for contributor in data:
        # BUG FIX HERE: Check if the GitHub account exists
        if contributor.get('author'):
            github_author = contributor['author']['login']
        else:
            github_author = "Account_Not_Configured"

        commits = contributor['total']
        total_team_commits += commits

        additions = sum(week['a'] for week in contributor['weeks'])
        deletions = sum(week['d'] for week in contributor['weeks'])

        # Associate the found email with the author
        found_emails = local_identities.get(github_author, "Unknown_Email")

        team_stats.append({
            "Team_name": team_name,
            "Link": link,
            "GitHub_Author": github_author,
            "Local_Git_Identities": found_emails,
            "Commits": commits,
            "Lines_Added": additions,
            "Lines_Deleted": deletions
        })

    # Calculate participation percentage
    for member in team_stats:
        percentage = (member['Commits'] / total_team_commits) * 100 if total_team_commits > 0 else 0
        member['Commit_Percentage'] = round(percentage, 2)

    return team_stats

# --- MAIN PROGRAM ---
print("🚀 Starting GitHub data extraction...")

# Check if a CSV input file is provided as command-line argument
if len(sys.argv) > 1:
    input_csv_file = sys.argv[1]
    if os.path.isfile(input_csv_file):
        print(f"📁 Using provided CSV file: {input_csv_file}")
        # Load the CSV file directly (skip GitHub extraction)
        df = pd.read_csv(input_csv_file, sep=',')
        df.fillna(0, inplace=True)
    else:
        print(f"❌ Error: File {input_csv_file} not found.")
        exit(1)
else:
    # Extract data from GitHub
    print("📡 Extracting data from GitHub ...")
    
    unprocessed_teams = []
    all_stats = []
    failed_teams = []

    with open(INPUT_TEAM_FILE, mode='r', encoding='utf-8') as input_csv:
        reader = csv.DictReader(input_csv)
        
        for row in reader:
            try:
                team_name = row['TeamName']
                link = row['GitLink']
                owner, repo = extract_owner_repo(link)

                if not owner or not repo:
                    print(f"⚠️ Invalid link for {team_name} : {link}")
                    unprocessed_teams.append({
                        'TeamName': team_name,
                        'GitLink': link,
                        'Error': 'Invalid link'
                    })
                    continue

                print(f"📊 Analyzing team {team_name} ({owner}/{repo})...")
                stats = get_contributor_stats(owner, repo, team_name, link)

                if not stats:
                    failed_teams.append({'team_name': team_name, 'link': link})
                else:
                    all_stats.extend(stats)
            except Exception as e:
                print(f"❌ Unexpected error processing team: {e}")
                unprocessed_teams.append({
                    'TeamName': row.get('TeamName', 'UNKNOWN'),
                    'GitLink': row.get('GitLink', 'UNKNOWN'),
                    'Error': str(e)
                })
                continue

    # Retry failed teams until no more NO_DATA
    retry_count = 0
    max_retries = 5  # Prevent infinite loops
    while failed_teams and retry_count < max_retries:
        retry_count += 1
        print(f"🔄 Retry {retry_count}/{max_retries}: {len(failed_teams)} failed teams...")
        
        new_failed = []
        for team in failed_teams:
            try:
                owner, repo = extract_owner_repo(team['link'])
                if owner and repo:
                    print(f"   📊 Retrying team {team['team_name']} ({owner}/{repo})...")
                    stats = get_contributor_stats(owner, repo, team['team_name'], team['link'])
                    if stats:
                        all_stats.extend(stats)
                    else:
                        new_failed.append(team)
                else:
                    new_failed.append(team)
            except Exception as e:
                print(f"   ❌ Error retrying {team['team_name']}: {e}")
                new_failed.append(team)
        
        failed_teams = new_failed
        if failed_teams:
            print(f"   ⏳ Still {len(failed_teams)} failed, waiting 10s before next retry...")
            time.sleep(10)

    # Add NO_DATA entries for remaining failed teams
    for team in failed_teams:
        all_stats.append({
            'Team_Name': team['team_name'], 'Link': team['link'], 'GitHub_Author': 'NO_DATA', 
            'Local_Git_Identities': '', 'Commits': 0, 'Commit_Percentage': 0, 
            'Lines_Added': 0, 'Lines_Deleted': 0
        })
        unprocessed_teams.append({
            'TeamName': team['team_name'],
            'GitLink': team['link'],
            'Error': 'NO_DATA after retries'
        })

    # Convert to DataFrame
    df = pd.DataFrame(all_stats)
    df.fillna(0, inplace=True)

    # Save the GitHub contribution data
    df.to_csv(OUTPUT_GITHUB_CONTRIBUTION_DATA, index=False, sep=',')
    print(f"📁 GitHub contribution data saved to '{OUTPUT_GITHUB_CONTRIBUTION_DATA}'.")

    # Create unprocessed teams file if there are any errors
    if unprocessed_teams:
        with open(UNPROCESSED_FILE, mode='w', encoding='utf-8', newline='') as unprocessed_file:
            unprocessed_fields = ['TeamName', 'GitLink', 'Error']
            unprocessed_writer = csv.DictWriter(unprocessed_file, fieldnames=unprocessed_fields)
            unprocessed_writer.writeheader()
            unprocessed_writer.writerows(unprocessed_teams)
        print(f"⚠️ {len(unprocessed_teams)} unprocessed team(s) saved to '{UNPROCESSED_FILE}'.")
    else:
        print(f"✅ All teams processed successfully!")

# 2. Grading function
def evaluate_on_20(row):
    pct_str = row['Commit_Percentage']
    if isinstance(pct_str, str):
        pct = float(pct_str.strip('%'))
    else:
        pct = pct_str * 100  # assuming it's already a float like 0.1143
    commits = row['Commits']
    lines = row['Lines_Added'] + row['Lines_Deleted']
    
    # Criterion 1: Balance (out of 10)
    if pct >= 15: balance_points = 10
    elif pct >= 10: balance_points = 7
    elif pct >= 5: balance_points = 4
    elif pct > 0: balance_points = 1
    else: balance_points = 0
        
    # Criterion 2: Regularity (out of 5)
    if commits >= 5: commits_points = 5
    elif commits >= 2: commits_points = 3
    elif commits == 1: commits_points = 1
    else: commits_points = 0
        
    # Criterion 3: Code (out of 5)
    if lines >= 200: lines_points = 5
    elif lines >= 50: lines_points = 3
    elif lines > 0: lines_points = 1
    else: lines_points = 0
        
    # Final Grade
    final_grade = balance_points + commits_points + lines_points
    
    return pd.Series([balance_points, commits_points, lines_points, final_grade])

# 3. Apply the grading scale
grade_columns = ['Git_Work_Balance_Pts_10', 'Commits_Pts_5', 'Lines_Pts_5', 'Participation_Score']
df[grade_columns] = df.apply(evaluate_on_20, axis=1)

# Final formatting
df['Commit_Percentage'] = df['Commit_Percentage'].apply(lambda x: f"{float(x.strip('%')):.2f}%" if isinstance(x, str) else f"{x:.2f}%")

# 4. Enrich output with students_profile.csv columns via GitHub_Author join
try:
    students_profile = pd.read_csv(INPUT_STUDENTS_PROFILE_FILE)
except FileNotFoundError:
    print(f"❌ Error: File {INPUT_STUDENTS_PROFILE_FILE} not found. Cannot create enriched output.")
else:
    # Merge existing evaluation result with students profile fields by GitHub_Author
    enriched_output = pd.merge(
        students_profile,
        df,
        on='GitHub_Author',
        how='left',
        suffixes=('', '_profile')
    )

    # Fill NaN values for students without GitHub data
    enriched_output.fillna({
        'Link': '',
        'Local_Git_Identities': '',
        'Commits': 0,
        'Commit_Percentage': '0.00%',
        'Lines_Added': 0,
        'Lines_Deleted': 0,
        'Git_Work_Balance_Pts_10': 0,
        'Commits_Pts_5': 0,
        'Lines_Pts_5': 0,
        'Participation_Score': 0
    }, inplace=True)

    # Select only the specified columns
    selected_columns = [
        'Team_number', 'Team_name', 'hidden_id', 'GitHub_Author',
        'Python_Level', 'AI_Usage_for_Coding', 'Unit_Tests',
        'Link', 'Local_Git_Identities', 'Commits', 'Commit_Percentage',
        'Lines_Added', 'Lines_Deleted', 'Git_Work_Balance_Pts_10',
        'Commits_Pts_5', 'Lines_Pts_5', 'Participation_Score'
    ]
    enriched_output = enriched_output[selected_columns]

    # Exclude teacher account (sof-coder)
    enriched_output = enriched_output[enriched_output['GitHub_Author'] != 'sof-coder']

    # Save the enriched file
    enriched_output.to_csv(ENRICHED_OUTPUT_FILE, index=False, sep=';')
    print(f"✅ Enriched evaluation file '{ENRICHED_OUTPUT_FILE}' has been created with selected columns.")

print(f"✅ Done! Results saved to '{ENRICHED_OUTPUT_FILE}'.")
print("\n📝 Usage:")
print("   Without arguments: python en_student_evaluation.py")
print("   With CSV input:   python en_student_evaluation.py <path_to_csv_file>")

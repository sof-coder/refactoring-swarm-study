# Refactoring Swarm Study

This repository contains the deliverables, data, and analysis scripts for a software engineering experiment focused on "refactoring swarms".

This repository contains the deliverables, data, analysis scripts, and experimental materials for the paper “The Refactoring Swarm: An Empirical Study of Code Self-Repair by Multi-Agent (LLM) Systems in an Academic Context”

"Empirical Evaluation of LLM-based Multi-Agent Systems for Code Refactoring: Performance, Expertise, and Behavioral Dynamics"

## Project Structure

The repository is organized into four main directories:

- **`1_materials/`**: Contains the documentation and resources provided to participants or used in the administration of the experiment.
  - `Document 1 - Statement of the IGL Lab (2025-2026) - English version.pdf`: The problem statement and instructions for the IGL Lab.
  - `Document 2 - Technical Configuration Guide -English version.pdf`: Guide for participants to set up their technical environment.
  - `refactoring-swarm-template.zip`: The template code/repository provided to participants.
  - `grading/`: Contains evaluation scripts and datasets for grading student and team submissions (see its own `README.md` for more details).
  - `hidden_dataset/`: Additional hidden datasets used for testing or validation.

- **`2_data/`**: Contains the raw and processed datasets resulting from the experiment.
  - `en_data_teams.csv` & `global_student_evaluation.csv`: Tabular data regarding team and individual evaluations.
  - `hacktown_experiment_data.zip` & `history_experiment_data.zip`: Archived application state data or codebase snapshots from the experiment.

- **`3_scripts/`**: Python scripts used to analyze the dataset and answer specific research questions (grouped into different axes).
  - `axis_1_2_3_analysis_v2.py`: Analysis script for research axes 1, 2, and 3.
  - `axis_4_analysis_v2.py`: Analysis script for research axis 4.
  - `requirements.txt`: Python package dependencies required to run the analysis scripts.

- **`4_results/`**: Output directories where the analysis scripts save their generated charts, metrics, and interpretation files.
  - `research_results_axis_1_2_3/`: Results from axes 1, 2, and 3.
  - `research_results_axis_4/`: Results from axis 4.

## Setup and Usage

To run the data analysis scripts located in the `3_scripts` directory, follow these steps:

### Prerequisites

- Python 3.10 or higher installed on your system.

### Installation & Execution

1. Clone the repository and navigate to the `3_scripts` directory:
   ```bash
   cd refactoring-swarm-study/3_scripts
   ```

2. Install the required external Python dependencies using `pip`:
   ```bash
   pip install -r requirements.txt
   ```
   *(Dependencies include libraries like `pandas`, `numpy`, `matplotlib`, `seaborn`, and `scipy`.)*

3. Execute the analysis scripts:
   ```bash
   python axis_1_2_3_analysis_v2.py
   python axis_4_analysis_v2.py
   ```

4. Check the `4_results/` directory for the newly generated output files.

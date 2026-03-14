# Replication Package: The Refactoring Swarm
This repository contains the data, analysis scripts, and experimental materials for the paper “The Refactoring Swarm: An Empirical Study of Code Self-Repair by Multi-Agent (LLM) Systems in an Academic Context”
## 📊 Repository Structure
* /1_materials/: Contains the hidden_dataset used to evaluate the LLM swarms and the lab instructions given to students.
* /2_data/: Contains the fully anonymized dataset ($N=262$ students, 64 valid JSON traces).
* /3_scripts/: Python scripts used to generate the statistical findings (Pearson correlations, p-values) and figures presented in the paper.
* /4_results/: The output artifacts (CSV matrices and PNG figures).
## 🚀 How to Reproduce the Analysis
* Clone this repository.
* Install dependencies: pip install -r 3_scripts/requirements.txt
* Run the main analysis script: python 3_scripts/analyse_axes_1_2_3.py
* Check the /4_results/ folder for the newly generated graphs.
## ⚖️ License and Ethics
All student data has been strictly anonymized (matriculation numbers replaced by random IDs) in accordance with the university's ethical guidelines for Educational Data Mining.

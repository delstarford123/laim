# Contributing to Livestock AI-Manager

Thank you for your interest in contributing! We welcome help from developers, data scientists, and veterinarians.

## How to Contribute

### 1. Reporting Bugs
* Ensure the bug was not already reported by searching on GitHub under [Issues].
* If you're unable to find an open issue addressing the problem, open a new one. Be sure to include a title and clear description, as well as a code sample or an executable test case demonstrating the expected behavior that is not occurring.

### 2. Improving the Model
* If you have a larger dataset of cow records, please open a Pull Request adding it to the `data/` folder (anonymized).
* If you want to tweak the hyperparameters of the XGBoost model, please modify `src/train.py` and explain your reasoning in the PR.

### 3. Pull Requests
* Open a new GitHub pull request with the patch.
* Ensure the PR description clearly describes the problem and solution.
* Include the relevant issue number if applicable.

## Coding Standards
* Python: We use PEP 8.
* Commits: Use semantic commit messages (e.g., `feat: added random forest classifier`, `fix: corrected date parsing`).
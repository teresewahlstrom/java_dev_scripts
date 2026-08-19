# Scripts in this project
From the backend project folder (`backend/projects/game-1`), run the following:

## Run simulator
```powershell
.\scripts\run-sim.ps1 -Spins 10000000 -Seed 12345 -PassThru
```

## Run Dependency Visualization
To visualize the project dependencies:
```bash
# Flowchart Code Dependency Visualization horizontal
python scripts/generate_dependency_dot.py --dark --rankdir LR --dpi 400

# Flowchart Code Dependency Visualization vertical
python scripts/generate_dependency_dot.py --dark --rankdir TB --dpi 400
```

## Run Mermaid to Dot Visualization
To visualize a mermaid flowchart in a markdown document:
```bash
python scripts/mermaid_to_dot.py --md <path_to_markdown_file>
```

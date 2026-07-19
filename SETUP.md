# Setup Guide

This project is designed for the special GitHub profile repository `idcare19/idcare19`.
The instructions below start with Windows PowerShell because that is the primary environment for this workspace.

## 1) Create the GitHub profile repository

1. Sign in to GitHub.
2. Create a new public repository named exactly `idcare19`.
3. Make sure the repository owner is the GitHub account `idcare19`.
4. Add a README only if you want GitHub to create the initial file, but this project already includes a complete README.

## 2) Clone the repository

```powershell
git clone https://github.com/idcare19/idcare19.git
cd idcare19
```

## 3) Copy the generated project files

Copy the contents of this project folder into the cloned repository root so the structure matches the required layout.

## 4) Create a Python virtual environment

```powershell
python -m venv .venv
```

## 5) Activate it in PowerShell

```powershell
. .\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, use:

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
```

## 6) Install the lightweight daily dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r scripts/requirements.txt
```

These are the only packages needed by the daily GitHub Actions workflow.

## 7) Install portrait dependencies separately

```powershell
python -m pip install -r scripts/requirements-portrait.txt
```

Install these only when you need to regenerate the portrait locally.

## 8) Add the source photo

Place the uploaded portrait in the repository root as:

```powershell
source-photo.jpg
```

The workspace already provides `image.png`, so you can copy it first if needed.

## 9) Run the photo prep step

```powershell
python scripts/prep_photo.py source-photo.jpg
```

This creates `source-prepped.png`.

## 10) Generate the ASCII portrait

```powershell
python scripts/make_ascii_svg.py
```

Static mode:

```powershell
$env:STATIC = "1"
python scripts/make_ascii_svg.py
Remove-Item Env:STATIC
```

## 11) Generate the info card

```powershell
python scripts/make_info_card.py
```

Static mode:

```powershell
$env:STATIC = "1"
python scripts/make_info_card.py
Remove-Item Env:STATIC
```

## 12) Fetch contribution data

```powershell
python scripts/fetch_contributions.py
```

This reads public HTML from GitHub and writes `data/contributions.json`.

## 13) Render the heatmap SVG

```powershell
python scripts/render_heatmap_svg.py
```

Static mode:

```powershell
$env:STATIC = "1"
python scripts/render_heatmap_svg.py
Remove-Item Env:STATIC
```

## 14) Preview the SVG files locally

Open these files in a browser or image viewer:

- `README.md`
- `ascii-portrait.svg`
- `info-card.svg`
- `contrib-heatmap.svg`

If you use VS Code, the SVG preview extension also works well.

## 15) Commit and push

```powershell
git status
git add README.md ascii-portrait.svg info-card.svg contrib-heatmap.svg source-photo.jpg source-prepped.png data\contributions.json scripts .github .gitignore SETUP.md
git commit -m "chore: add profile art"
git push origin main
```

## 16) Run the workflow manually

1. Open the repository on GitHub.
2. Go to the **Actions** tab.
3. Select **Update profile art**.
4. Click **Run workflow**.

## 17) Enable workflow write permissions

If GitHub blocks bot commits:

1. Open repository settings.
2. Go to **Actions** -> **General**.
3. Set workflow permissions to **Read and write permissions**.
4. Save the change.

## 18) Troubleshoot Windows execution policy

If PowerShell blocks scripts:

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
```

This only affects the current PowerShell session.

## 19) Troubleshoot rembg or onnxruntime errors

If `rembg` fails to install or load:

1. Reinstall portrait dependencies in a clean virtual environment.
2. Make sure `onnxruntime` matches your Python version.
3. If necessary, regenerate the portrait after confirming `Pillow`, `numpy`, and `opencv-python` are installed.

The prep script falls back to OpenCV GrabCut if `rembg` is unavailable, but the preferred production path is still `rembg`.

## 20) Troubleshoot GitHub contribution parser failures

If GitHub changes the contributions HTML and the fetch step fails:

1. Open `https://github.com/users/idcare19/contributions` in a browser.
2. Compare the current DOM with the selectors in `scripts/fetch_contributions.py`.
3. Update the parser to follow the new `data-date` or accessibility attributes.
4. Re-run the fetch script locally before pushing.

## Copy-paste PowerShell block

```powershell
git clone https://github.com/idcare19/idcare19.git
cd idcare19
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r scripts/requirements.txt
python -m pip install -r scripts/requirements-portrait.txt
Copy-Item .\image.png .\source-photo.jpg
python scripts\prep_photo.py source-photo.jpg
python scripts\make_ascii_svg.py
python scripts\make_info_card.py
python scripts\fetch_contributions.py
python scripts\render_heatmap_svg.py
git add README.md ascii-portrait.svg info-card.svg contrib-heatmap.svg source-photo.jpg source-prepped.png data\contributions.json scripts .github .gitignore SETUP.md
git commit -m "chore: add profile art"
git push
```


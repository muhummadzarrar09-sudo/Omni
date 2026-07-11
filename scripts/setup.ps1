Write-Host "OMNI V2 Setup - Phase 1" -ForegroundColor Cyan
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Write-Host "Done! Run python omni.py --test" -ForegroundColor Green


# Build FORGE Windows deployment and migration ZIPs from repository root.
# Run: python scripts/build_windows_deployment.py
import json, os, shutil, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "windows-deployment"
APP_ZIP = OUT / "FORGE-Windows-Deployment.zip"
DATA_ZIP = OUT / "FORGE-Data-Migration.zip"
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".angular", "coverage"}
SKIP_FILES = {".DS_Store", "Thumbs.db"}

CADDY = r'''{
    admin off
}
:8080 {
    encode zstd gzip
    root * frontend/dist/forge-ui/browser
    @api path /api/*
    handle @api { reverse_proxy 127.0.0.1:8000 }
    @health path /health
    handle @health { reverse_proxy 127.0.0.1:8000 }
    handle {
        try_files {path} /index.html
        file_server
    }
}
'''
INSTALL = r'''$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Install approved 64-bit Python 3.11 first." }
py -3.11 --version
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 not found." }
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "Install uv from the approved software source first." }
Push-Location $Root
try {
  uv sync --locked --no-dev --no-group experiments
  if ($LASTEXITCODE -ne 0) { throw "uv dependency installation failed." }
  & "$Root\.venv\Scripts\python.exe" "$PSScriptRoot\prepare_config.py"
  if ($LASTEXITCODE -ne 0) { throw "Config preparation failed." }
  New-Item -ItemType Directory -Force -Path "$Root\logs","$Root\run","$Root\tools" | Out-Null
  if (-not (Test-Path "$Root\tools\caddy.exe")) { Write-Warning "Caddy is not bundled or assumed approved. Confirm the approved web server with IT." }
  Write-Host "Install preparation complete. Review backend\api\config before starting."
} finally { Pop-Location }
'''
PREPARE = r'''import json, secrets
from pathlib import Path
root = Path(__file__).resolve().parents[1]
templates = Path(__file__).resolve().parent / "config-templates"
cfg = root / "backend" / "api" / "config"
cfg.mkdir(parents=True, exist_ok=True)
for name in ("ai.json", "email.json"):
    dest = cfg / name
    if not dest.exists():
        obj = json.loads((templates / (name + ".template")).read_text(encoding="utf-8"))
        dest.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
dest = cfg / "authentication.json"
if not dest.exists():
    obj = json.loads((templates / "authentication.json.template").read_text(encoding="utf-8"))
    obj.setdefault("development_token", {})["secret"] = secrets.token_urlsafe(48)
    dest.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
print("Config files prepared; existing files were not overwritten.")
'''
START = r'''$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Run = "$Root\run"; $Logs = "$Root\logs"
New-Item -ItemType Directory -Force -Path $Run,$Logs | Out-Null
$python = "$Root\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Run deployment\Install-FORGE.ps1 first." }
$apiPidFile = "$Run\api.pid"
if (Test-Path $apiPidFile) {
  $id = 0; [int]::TryParse((Get-Content $apiPidFile -Raw).Trim(),[ref]$id) | Out-Null
  if (-not ($id -gt 0 -and (Get-Process -Id $id -ErrorAction SilentlyContinue))) { Remove-Item $apiPidFile -Force }
}
if (-not (Test-Path $apiPidFile)) {
  $p = Start-Process $python -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000") -WorkingDirectory "$Root\backend\api" -RedirectStandardOutput "$Logs\api.stdout.log" -RedirectStandardError "$Logs\api.stderr.log" -PassThru -WindowStyle Hidden
  Set-Content $apiPidFile $p.Id -NoNewline
}
$ready = $false
for ($i=0; $i -lt 30; $i++) { Start-Sleep 1; try { Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 2 | Out-Null; $ready=$true; break } catch {} }
if (-not $ready) { Write-Warning "API health failed; inspect logs\api.stderr.log"; exit 1 }
$caddy = "$Root\tools\caddy.exe"; $pidFile = "$Run\caddy.pid"
if (Test-Path $caddy) {
  if (Test-Path $pidFile) {
    $id=0; [int]::TryParse((Get-Content $pidFile -Raw).Trim(),[ref]$id) | Out-Null
    if (-not ($id -gt 0 -and (Get-Process -Id $id -ErrorAction SilentlyContinue))) { Remove-Item $pidFile -Force }
  }
  if (-not (Test-Path $pidFile)) {
    $p=Start-Process $caddy -ArgumentList @("run","--config","$PSScriptRoot\Caddyfile","--adapter","caddyfile") -WorkingDirectory $Root -RedirectStandardOutput "$Logs\web.stdout.log" -RedirectStandardError "$Logs\web.stderr.log" -PassThru -WindowStyle Hidden
    Set-Content $pidFile $p.Id -NoNewline
  }
  Write-Host "FORGE UI: http://localhost:8080"
} else { Write-Warning "API is up on 127.0.0.1:8000, but the UI needs an IT-approved web server." }
'''
STOP = r'''$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
foreach ($name in @("caddy.pid","api.pid")) {
  $file = "$Root\run\$name"
  if (Test-Path $file) {
    $id=0; [int]::TryParse((Get-Content $file -Raw).Trim(),[ref]$id) | Out-Null
    if ($id -gt 0 -and (Get-Process -Id $id -ErrorAction SilentlyContinue)) { Stop-Process -Id $id -ErrorAction SilentlyContinue; Write-Host "Stopped PID $id" }
    Remove-Item $file -Force -ErrorAction SilentlyContinue
  }
}
'''
HEALTH = r'''foreach ($url in @("http://127.0.0.1:8000/health","http://127.0.0.1:8080/health")) {
  try { $r=Invoke-WebRequest -Uri $url -TimeoutSec 5; Write-Host "$url -> HTTP $([int]$r.StatusCode)"; if ($r.Content) { Write-Host $r.Content } }
  catch { Write-Warning "$url -> FAILED: $($_.Exception.Message)" }
}
'''
DIAGNOSE = r'''$Root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Write-Host "FORGE root: $Root"
if (Get-Command py -ErrorAction SilentlyContinue) { py -3.11 --version } else { Write-Warning "Python launcher missing" }
if (Get-Command uv -ErrorAction SilentlyContinue) { uv --version } else { Write-Warning "uv missing" }
foreach ($p in @("backend\api\config\ai.json","backend\api\config\email.json","backend\api\config\authentication.json",".venv\Scripts\python.exe","frontend\dist\forge-ui\browser\index.html","tools\caddy.exe")) { Write-Host ("{0}: {1}" -f $p,(Test-Path (Join-Path $Root $p))) }
& "$PSScriptRoot\Health-FORGE.ps1"
foreach ($p in @("logs\api.stderr.log","logs\web.stderr.log")) { $f=Join-Path $Root $p; if (Test-Path $f) { Write-Host "[$p]"; Get-Content $f -Tail 30 } }
'''
RESTORE = r'''param([Parameter(Mandatory=$true)][string]$MigrationArchive)
$ErrorActionPreference="Stop"
$Root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Archive=(Resolve-Path $MigrationArchive).Path
$stamp=Get-Date -Format "yyyyMMdd-HHmmss"
New-Item -ItemType Directory -Force -Path "$Root\backups" | Out-Null
$temp=Join-Path $env:TEMP ("forge-migration-"+[guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temp | Out-Null
try {
  Expand-Archive -LiteralPath $Archive -DestinationPath $temp -Force
  $source="$temp\backend\api\data"
  if (-not (Test-Path "$temp\manifest.json") -or -not (Test-Path $source)) { throw "Invalid FORGE migration archive layout." }
  $target="$Root\backend\api\data"
  if (Test-Path $target) { Move-Item -LiteralPath $target -Destination "$Root\backups\data-$stamp" }
  New-Item -ItemType Directory -Force -Path $target | Out-Null
  Copy-Item -Path "$source\*" -Destination $target -Recurse -Force
  Write-Host "Migration restored. Previous data backup: $Root\backups\data-$stamp"
} finally { Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue }
'''
GUIDE = r'''# FORGE Windows Deployment Guide

1. Confirm Windows version, hostname/DNS, firewall, service-account policy, and the company-approved web server with IT. The included Caddyfile is a reference only; Caddy is not bundled or assumed approved.
2. Install approved 64-bit Python 3.11 and `uv`. The target needs access to the approved Python package source.
3. Extract `FORGE-Windows-Deployment.zip` to a stable path such as `C:\FORGE`.
4. Run PowerShell from the extracted root: `.\deployment\Install-FORGE.ps1`.
5. Review `backend\api\config\ai.json` and `email.json`. Set the approved Ollama endpoint/model, SMTP host/port/sender, public HTTPS magic-link URL and STARTTLS settings. If SMTP authentication is required, set `FORGE_SMTP_PASSWORD` in the service/process environment, never in JSON. Ensure HTTPS access and corporate certificate trust for the corporate profile API.
6. The installer generates a fresh random authentication secret if `authentication.json` does not exist. Keep it private and review `allowed_domains`.
7. Review the migration manifest, then restore data: `.\deployment\Restore-FORGE-Data.ps1 -MigrationArchive C:\path\FORGE-Data-Migration.zip`. Existing data is moved under `backups\` first.
8. If IT approves Caddy, place its approved Windows binary at `tools\caddy.exe` and review `deployment\Caddyfile`. It listens on port 8080 and proxies `/api/*` and `/health` to `127.0.0.1:8000`. Otherwise configure approved IIS/proxy to serve `frontend\dist\forge-ui\browser`, preserve those API paths, and use SPA fallback to `index.html`.
9. Run `.\deployment\Start-FORGE.ps1`; verify with `.\deployment\Health-FORGE.ps1`; diagnose with `.\deployment\Diagnose-FORGE.ps1`; stop with `.\deployment\Stop-FORGE.ps1`.

The API binds to loopback only and must not be exposed directly. The reference UI URL is `http://localhost:8080`; magic links must use the actual externally reachable HTTPS URL. Ollama/model, SMTP and corporate profile API connectivity need separate verification; `/health` alone does not verify them. The migration ZIP contains internal user/profile data and must be transferred only through an approved corporate channel. It preserves model directories and backups, but excludes the known `validation-store-test` directory, live sessions, and generation execution state. The included start/stop scripts are helpers, not a Windows service wrapper; apply approved ACLs, service supervision and log rotation.

## Rebuild archives
From the FORGE repository root run `python scripts/build_windows_deployment.py`. Output: `dist\windows-deployment\FORGE-Windows-Deployment.zip` and `dist\windows-deployment\FORGE-Data-Migration.zip`. Rebuild the Angular production bundle first when frontend source changes, then review the migration manifest and both ZIPs before transfer.
'''

def die(message):
    raise SystemExit("ERROR: " + message)

def read_json(path):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: die(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}")

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def copy_tree(source, target, exclude_generation=False):
    for current, dirs, files in os.walk(source):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith(".") and (not exclude_generation or d.lower() != "generation"))
        cur = Path(current)
        dest = target / cur.relative_to(source)
        dest.mkdir(parents=True, exist_ok=True)
        for name in sorted(files):
            if name in SKIP_FILES or name.endswith((".pyc", ".pyo")): continue
            src = cur / name
            if not src.is_symlink(): shutil.copy2(src, dest / name)

def zip_tree(folder, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=8) as zf:
        for p in sorted(folder.rglob("*")):
            if p.is_file() and not p.is_symlink(): zf.write(p, p.relative_to(folder).as_posix())

def main():
    required = ["pyproject.toml","uv.lock",".python-version","backend/api/app","backend/api/config/ai.json","backend/api/config/email.json","backend/api/config/authentication.json","frontend/dist/forge-ui/browser/index.html","backend/api/data/data_models.json","backend/api/data/users.json"]
    missing = [p for p in required if not (ROOT / p).exists()]
    if missing: die("Missing inputs: " + ", ".join(missing) + ". Build the Angular production bundle first if needed.")
    if (ROOT/".python-version").read_text(encoding="utf-8").strip() != "3.11": die("Expected .python-version to be 3.11.")
    ai=read_json(ROOT/"backend/api/config/ai.json")
    email=read_json(ROOT/"backend/api/config/email.json")
    auth=read_json(ROOT/"backend/api/config/authentication.json")
    data=ROOT/"backend/api/data"
    meta=read_json(data/"data_models.json")
    user_obj=read_json(data/"users.json")
    activity_obj=read_json(data/"activities.json") if (data/"activities.json").exists() else {}
    access_obj=read_json(data/"data_model_access.json") if (data/"data_model_access.json").exists() else {}
    models=meta if isinstance(meta,list) else meta.get("data_models",meta.get("dataModels",[]))
    users=user_obj if isinstance(user_obj,list) else user_obj.get("users",[])
    activities=activity_obj if isinstance(activity_obj,list) else activity_obj.get("activities",[])
    accesses=access_obj if isinstance(access_obj,list) else access_obj.get("access",access_obj.get("data_model_access",[]))
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="forge-app-") as td:
        stage=Path(td)
        for name in ("pyproject.toml","uv.lock",".python-version"): shutil.copy2(ROOT/name,stage/name)
        if (ROOT/"LICENSE").is_file(): shutil.copy2(ROOT/"LICENSE",stage/"LICENSE")
        copy_tree(ROOT/"backend/api/app",stage/"backend/api/app")
        (stage/"backend/api/config").mkdir(parents=True,exist_ok=True)
        (stage/"backend/api/config/.gitkeep").write_text("",encoding="utf-8")
        (stage/"backend/api/data").mkdir(parents=True,exist_ok=True)
        (stage/"backend/api/data/.gitkeep").write_text("",encoding="utf-8")
        copy_tree(ROOT/"frontend/dist/forge-ui/browser",stage/"frontend/dist/forge-ui/browser")
        dep=stage/"deployment"; tpl=dep/"config-templates"; tpl.mkdir(parents=True)
        write_json(tpl/"ai.json.template",ai)
        safe_email=json.loads(json.dumps(email))
        smtp=safe_email.setdefault("smtp",{}); smtp["host"]="REPLACE_WITH_APPROVED_SMTP_HOST"; smtp["sender"]="REPLACE_WITH_APPROVED_SENDER"; smtp["username"]=""
        safe_email.setdefault("magic_link",{})["frontend_base_url"]="https://REPLACE-WITH-FORGE-HOST"
        write_json(tpl/"email.json.template",safe_email)
        tok=auth.get("development_token",{})
        write_json(tpl/"authentication.json.template",{"allowed_domains":auth.get("allowed_domains",[]),"development_token":{"algorithm":tok.get("algorithm","HS256"),"expiration_minutes":tok.get("expiration_minutes",60),"secret":"GENERATED-ON-TARGET"}})
        for name,content in {"Caddyfile":CADDY,"Install-FORGE.ps1":INSTALL,"prepare_config.py":PREPARE,"Start-FORGE.ps1":START,"Stop-FORGE.ps1":STOP,"Health-FORGE.ps1":HEALTH,"Diagnose-FORGE.ps1":DIAGNOSE,"Restore-FORGE-Data.ps1":RESTORE,"DEPLOYMENT-GUIDE.md":GUIDE}.items():
            (dep/name).write_text(content,encoding="utf-8")
        (stage/"README-DEPLOYMENT.md").write_text("Read deployment/DEPLOYMENT-GUIDE.md before installing. This archive contains no runtime data or production authentication secret.\n",encoding="utf-8")
        zip_tree(stage,APP_ZIP)
    with tempfile.TemporaryDirectory(prefix="forge-data-") as td:
        stage=Path(td); md=stage/"backend/api/data"; md.mkdir(parents=True)
        for name in ("activities.json","data_models.json","data_model_access.json","users.json"):
            if (data/name).exists(): shutil.copy2(data/name,md/name)
        write_json(md/"sessions.json",{"sessions":[]})
        dirs=[]; excluded=[]
        source_models=data/"data_model"
        if source_models.exists():
            for child in sorted(source_models.iterdir()):
                if not child.is_dir(): continue
                if child.name.lower()=="validation-store-test": excluded.append(child.name); continue
                copy_tree(child,md/"data_model"/child.name,exclude_generation=True); dirs.append(child.name)
        registered={str(m.get("data_model_id")) for m in models if isinstance(m,dict) and m.get("data_model_id")}
        orphan=[name for name in dirs if name not in registered]
        specs=sum(1 for p in (md/"data_model").rglob("specification.json")) if (md/"data_model").exists() else 0
        manifest={"package":"FORGE-Data-Migration","created_at_utc":datetime.now(timezone.utc).isoformat(),"scope":"Reviewed JSON runtime data, model specifications and backups; no live sessions or generation execution state","counts":{"registered_data_models":len(models),"users":len(users),"activities":len(activities),"access_records":len(accesses),"model_directories_preserved":len(dirs),"specification_files":specs},"preserved_model_directories":dirs,"unregistered_model_directories_preserved":orphan,"excluded_directories":excluded,"notes":["Sessions reset to empty; do not migrate authentication sessions across hosts.","Generation execution state excluded to avoid stale jobs, checkpoints and artifacts.","Known validation-store-test directory excluded.","Review unresolved historical user/model references and specification backups after restoration; inconsistencies are preserved rather than silently edited.","Contains internal user/profile data; transfer only through an approved corporate channel."]}
        write_json(stage/"manifest.json",manifest); zip_tree(stage,DATA_ZIP)
    print("Created FORGE release archives:")
    for p in (APP_ZIP,DATA_ZIP): print(f"  {p.relative_to(ROOT)} ({p.stat().st_size:,} bytes)")
    print(f"Migration summary: models={len(models)}, users={len(users)}, activities={len(activities)}, access_records={len(accesses)}, model_dirs={len(dirs)}, specifications={specs}, orphan_dirs={len(orphan)}")
    if excluded: print("Excluded test directories: "+", ".join(excluded))
    print("Inspect the manifest and ZIPs before transfer.")
    return 0

if __name__ == "__main__": raise SystemExit(main())

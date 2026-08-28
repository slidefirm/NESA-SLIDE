param(
    [string]$PythonPath = $env:NESA_PYTHON
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    throw "Set NESA_PYTHON to the selected system CPython 3.13 executable. Codex bundled Python is not sufficient for NESA-SLIDE validation."
}
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "NESA_PYTHON does not resolve to an executable file."
}

$requiredNodeVariables = @("RUNTIME_NODE", "RUNTIME_NODE_MODULES", "RUNTIME_BIN_DIR")
foreach ($name in $requiredNodeVariables) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrWhiteSpace($value) -or -not (Test-Path -LiteralPath $value)) {
        throw "Set $name from Codex load_workspace_dependencies before running this check."
    }
}

$pythonVersion = (& $PythonPath -c "import sys; print('.'.join(map(str, sys.version_info[:3])))").Trim()
$yamlVersion = (& $PythonPath -c "import yaml; print(yaml.__version__)").Trim()
if ($yamlVersion -ne "6.0.3") {
    throw "Selected Python must provide PyYAML 6.0.3; found $yamlVersion."
}

$artifactTool = Join-Path $env:RUNTIME_NODE_MODULES "@oai\artifact-tool"
if (-not (Test-Path -LiteralPath $artifactTool)) {
    throw "Codex runtime node_modules does not contain @oai/artifact-tool."
}

[pscustomobject]@{
    status = "pass"
    python = @{ version = $pythonVersion; pyyaml = $yamlVersion; source = "NESA_PYTHON system-selected runtime" }
    node = @{ executable = $env:RUNTIME_NODE; modules = $env:RUNTIME_NODE_MODULES; bin = $env:RUNTIME_BIN_DIR; source = "Codex load_workspace_dependencies" }
    artifact_tool = "available"
    note = "This check validates runtime capability only; browser and PowerPoint still require artifact-specific QA."
} | ConvertTo-Json -Depth 4

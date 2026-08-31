const { spawnSync } = require("node:child_process");

function run(command, args) {
  const result = spawnSync(command, args, { cwd: process.cwd(), stdio: "inherit", shell: false });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}

function findPython() {
  const candidates = process.platform === "win32"
    ? [["py", ["-3"]], ["python", []]]
    : [["python3", []], ["python", []]];
  for (const [command, prefix] of candidates) {
    const probe = spawnSync(command, [...prefix, "--version"], { encoding: "utf8" });
    if (!probe.error && probe.status === 0) return { command, prefix };
  }
  throw new Error("Python 3.13+ is required");
}

run(process.execPath, ["scripts/sync_agent_skills.cjs", "--check"]);
if (process.platform === "win32") {
  run("powershell", ["-ExecutionPolicy", "Bypass", "-File", "scripts/audit.ps1"]);
} else {
  const python = findPython();
  const checks = [
    ["scripts/portable_manifest.py", "--check"],
    ["scripts/generate_renderer_adapters.py", "--check"],
    ["scripts/html_preset_registry.py"],
    ["scripts/verify_renderer_matrix.py"],
  ];
  for (const args of checks) run(python.command, [...python.prefix, ...args]);
  console.log("Cross-platform core audit passed. Windows-only PowerPoint checks were not run.");
}

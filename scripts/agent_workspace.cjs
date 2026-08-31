const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "..");

function findPython() {
  const candidates = [];
  if (process.env.NESA_PYTHON) candidates.push([process.env.NESA_PYTHON, []]);
  if (process.platform === "win32") candidates.push(["py", ["-3"]], ["python", []]);
  else candidates.push(["python3", []], ["python", []]);
  for (const [command, prefix] of candidates) {
    const probe = spawnSync(command, [...prefix, "--version"], { encoding: "utf8" });
    if (!probe.error && probe.status === 0) return { command, prefix };
  }
  return null;
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: root,
    stdio: "inherit",
    shell: false,
    ...options,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}

function installNodeDependencies() {
  if (process.env.npm_execpath && fs.existsSync(process.env.npm_execpath)) {
    run(process.execPath, [process.env.npm_execpath, "install", "--ignore-scripts"]);
    return;
  }
  if (process.platform === "win32") {
    run(process.env.ComSpec || "cmd.exe", ["/d", "/s", "/c", "npm install --ignore-scripts"]);
  } else {
    run("npm", ["install", "--ignore-scripts"]);
  }
}

function doctor() {
  const python = findPython();
  if (!python) {
    console.error("Python 3.13+ was not found. Install Python, then rerun npm run setup.");
    process.exit(1);
  }
  run(python.command, [...python.prefix, "CHECK_SYSTEM.py", "--skip-integrity"]);
  run(process.execPath, ["scripts/sync_agent_skills.cjs", "--check"]);
}

function setup() {
  const python = findPython();
  if (!python) {
    console.error("Python 3.13+ was not found. Install Python, then rerun npm run setup.");
    process.exit(1);
  }
  installNodeDependencies();
  if (!fs.existsSync(path.join(root, "node_modules"))) {
    console.error("Node.js dependencies were not installed.");
    process.exit(1);
  }
  run(python.command, [...python.prefix, "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements.txt"]);
  doctor();
  console.log("\nNESA-SLIDE is ready. Ask your agent to create a presentation, or run npm run demo.");
}

function mimeType(file) {
  const extension = path.extname(file).toLowerCase();
  return ({
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
  })[extension] || "application/octet-stream";
}

function demo() {
  const argumentIndex = process.argv.indexOf("--port");
  const requested = argumentIndex >= 0 ? Number(process.argv[argumentIndex + 1]) : Number(process.env.NESA_DEMO_PORT || 7394);
  const port = Number.isInteger(requested) && requested > 0 && requested < 65536 ? requested : 7394;
  const base = path.join(root, "demos", "html");
  const server = http.createServer((request, response) => {
    const requestPath = decodeURIComponent(new URL(request.url, `http://${request.headers.host}`).pathname);
    const relative = requestPath === "/" ? "index.html" : requestPath.replace(/^\/+/, "");
    const file = path.resolve(base, relative);
    if (file !== base && !file.startsWith(base + path.sep)) {
      response.writeHead(403).end("Forbidden");
      return;
    }
    fs.readFile(file, (error, data) => {
      if (error) {
        response.writeHead(error.code === "ENOENT" ? 404 : 500).end("Not found");
        return;
      }
      response.writeHead(200, { "Content-Type": mimeType(file), "Cache-Control": "no-store" });
      response.end(data);
    });
  });
  server.listen(port, "127.0.0.1", () => {
    console.log(`NESA-SLIDE demo: http://127.0.0.1:${port}/`);
    console.log("Press Ctrl+C to stop.");
  });
}

const action = process.argv[2];
if (action === "setup") setup();
else if (action === "doctor") doctor();
else if (action === "demo") demo();
else {
  console.log("Usage: node scripts/agent_workspace.cjs setup|doctor|demo [--port 7394]");
  process.exit(action ? 1 : 0);
}

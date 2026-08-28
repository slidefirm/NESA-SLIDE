const fs = require("node:fs");
const path = require("node:path");

function candidateModuleRoots() {
  const roots = [
    process.env.CODEX_NODE_MODULES,
    ...(process.env.NODE_PATH || "").split(path.delimiter),
    path.resolve(__dirname, "..", "node_modules"),
    process.env.USERPROFILE
      ? path.join(
          process.env.USERPROFILE,
          ".cache",
          "codex-runtimes",
          "codex-primary-runtime",
          "dependencies",
          "node",
          "node_modules"
        )
      : null,
  ];
  return [...new Set(roots.filter(Boolean).map((root) => path.resolve(root)))];
}

function loadPlaywright() {
  try {
    return require("playwright");
  } catch (localError) {
    for (const root of candidateModuleRoots()) {
      const candidate = path.join(root, "playwright");
      if (!fs.existsSync(path.join(candidate, "package.json"))) continue;
      return require(candidate);
    }
    throw new Error(
      "Playwright is unavailable. Install it locally or set CODEX_NODE_MODULES " +
      "to a node_modules directory containing playwright. Checked: " +
      candidateModuleRoots().join(", ")
    );
  }
}

function browserExecutable() {
  return [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ]
    .filter(Boolean)
    .find(fs.existsSync);
}

module.exports = { browserExecutable, loadPlaywright };

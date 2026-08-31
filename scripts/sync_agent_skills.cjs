const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const source = path.join(root, ".agents", "skills");
const target = path.join(root, ".claude", "skills");

function filesUnder(base) {
  if (!fs.existsSync(base)) return [];
  const output = [];
  const visit = (directory) => {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const absolute = path.join(directory, entry.name);
      if (entry.isDirectory()) visit(absolute);
      else if (entry.isFile()) output.push(path.relative(base, absolute).split(path.sep).join("/"));
    }
  };
  visit(base);
  return output.sort();
}

function digest(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

function compare() {
  const sourceFiles = filesUnder(source);
  const targetFiles = filesUnder(target);
  const sourceSet = new Set(sourceFiles);
  const targetSet = new Set(targetFiles);
  const missing = sourceFiles.filter((file) => !targetSet.has(file));
  const extra = targetFiles.filter((file) => !sourceSet.has(file));
  const changed = sourceFiles.filter((file) => (
    targetSet.has(file) && digest(path.join(source, file)) !== digest(path.join(target, file))
  ));
  return { sourceFiles: sourceFiles.length, targetFiles: targetFiles.length, missing, extra, changed };
}

function writeMirror() {
  if (!fs.existsSync(source)) throw new Error(`canonical Skill directory missing: ${source}`);
  fs.rmSync(target, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.cpSync(source, target, { recursive: true });
}

const mode = process.argv[2] || "--check";
if (mode === "--write") writeMirror();
else if (mode !== "--check") throw new Error("usage: node scripts/sync_agent_skills.cjs --check|--write");

const result = compare();
result.pass = result.missing.length === 0 && result.extra.length === 0 && result.changed.length === 0;
console.log(JSON.stringify(result));
if (!result.pass) process.exitCode = 1;

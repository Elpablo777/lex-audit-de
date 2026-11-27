import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const mode = process.argv[2] === "dev" ? "dev" : "start";
const webDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(webDir, "../..");
const nextEntry = path.join(webDir, "node_modules", "next", "dist", "bin", "next");

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8010";
const healthUrl = `${apiBaseUrl.replace(/\/$/, "")}/api/v1/health`;

function isLocalhostTarget(urlStr) {
  try {
    const parsed = new URL(urlStr);
    return parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost";
  } catch {
    return false;
  }
}

async function isApiHealthy() {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1200);
    const res = await fetch(healthUrl, { signal: ctrl.signal });
    clearTimeout(timer);
    return res.ok;
  } catch {
    return false;
  }
}

function findLocalUvicornCommand() {
  const apiMain = path.join(repoRoot, "apps", "api", "src", "lexaudit_api", "main.py");
  if (!existsSync(apiMain)) return null;

  const venvPythonWin = path.join(repoRoot, ".venv", "Scripts", "python.exe");
  const venvPythonPosix = path.join(repoRoot, ".venv", "bin", "python");
  const uvicornArgs = [
    "-m",
    "uvicorn",
    "lexaudit_api.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8010",
    "--timeout-keep-alive",
    "75",
  ];

  if (existsSync(venvPythonWin)) {
    return { cmd: venvPythonWin, args: uvicornArgs, cwd: repoRoot };
  }
  if (existsSync(venvPythonPosix)) {
    return { cmd: venvPythonPosix, args: uvicornArgs, cwd: repoRoot };
  }
  return {
    cmd: process.platform === "win32" ? "uv.exe" : "uv",
    args: ["run", "python", ...uvicornArgs],
    cwd: repoRoot,
  };
}

function killProcessTree(child) {
  if (!child || child.exitCode !== null || !child.pid) return;
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  } else {
    child.kill("SIGTERM");
  }
}

async function main() {
  let apiChild = null;
  const webOnly = process.env.LEXAUDIT_WEB_ONLY === "1";

  if (!webOnly && isLocalhostTarget(apiBaseUrl) && !(await isApiHealthy())) {
    const launcher = findLocalUvicornCommand();
    if (launcher) {
      console.log("[lexaudit] FastAPI auf 127.0.0.1:8010 läuft noch nicht — wird automatisch mitgestartet...");
      apiChild = spawn(launcher.cmd, launcher.args, {
        cwd: launcher.cwd,
        stdio: "inherit",
        shell: false,
      });
      apiChild.on("error", (err) => {
        console.warn(`[lexaudit] API-Autostart nicht möglich (${err.message}). Starte nur Web-Portal.`);
        apiChild = null;
      });

      const deadline = Date.now() + 20_000;
      while (Date.now() < deadline) {
        if (await isApiHealthy()) {
          console.log("[lexaudit] FastAPI-Backend bereit auf http://127.0.0.1:8010");
          break;
        }
        await new Promise((r) => setTimeout(r, 400));
      }
    }
  }

  const nextArgs =
    mode === "dev" ? ["dev", "-p", "3000", "-H", "127.0.0.1"] : ["start", "-p", "3000", "-H", "127.0.0.1"];
  const webChild = spawn(process.execPath, [nextEntry, ...nextArgs], {
    cwd: webDir,
    stdio: "inherit",
    shell: false,
  });

  const cleanup = () => {
    killProcessTree(webChild);
    killProcessTree(apiChild);
  };
  process.on("SIGINT", () => {
    cleanup();
    process.exit(0);
  });
  process.on("SIGTERM", () => {
    cleanup();
    process.exit(0);
  });
  process.on("exit", cleanup);

  webChild.on("exit", (code) => {
    killProcessTree(apiChild);
    process.exit(code ?? 0);
  });
}

main().catch((err) => {
  console.error("[lexaudit] Starter-Fehler:", err);
  process.exit(1);
});

import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

/// <reference types="node" />
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DEV_USER = {
  username: process.env.E2E_USERNAME || 'dev',
  password: process.env.E2E_PASSWORD || 'DevPassword!123',
  email: process.env.E2E_EMAIL || 'dev@example.com',
  displayName: process.env.E2E_DISPLAY_NAME || 'Dev User',
};

const resolvePythonExecutable = () => {
  const candidates = [
    process.env.PLAYWRIGHT_PYTHON,
    process.env.PYTHON,
    process.env.PYTHON_EXECUTABLE,
    'python',
    'python3',
    process.platform === 'win32' ? 'py' : undefined,
  ].filter(Boolean) as string[];

  for (const candidate of candidates) {
    try {
      execFileSync(candidate, ['--version'], { stdio: 'ignore' });
      return candidate;
    } catch {
      /* try next candidate */
    }
  }
  throw new Error('Unable to locate a Python interpreter. Set PLAYWRIGHT_PYTHON to the python executable path.');
};

const PYTHON_EXEC = resolvePythonExecutable();

function ensureDevUser() {
  const repoRoot = path.resolve(__dirname, '..', '..');
  const script = path.resolve(repoRoot, 'backend', 'scripts', 'create_dev_user.py');
  const pythonPath = path.resolve(repoRoot, 'backend');
  try {
    execFileSync(PYTHON_EXEC, [script,
      '--username', DEV_USER.username,
      '--password', DEV_USER.password,
      '--email', DEV_USER.email,
      '--display-name', DEV_USER.displayName,
    ], {
      stdio: 'inherit',
      cwd: repoRoot,
      env: {
        ...process.env,
        PYTHONPATH: pythonPath,
      },
    });
  } catch (error) {
    throw new Error(`Failed to seed dev user using ${PYTHON_EXEC}. Set PLAYWRIGHT_PYTHON to a valid interpreter. Original error: ${error}`);
  }
}

test.beforeAll(() => {
  ensureDevUser();
});

test('dev login and open review queue', async ({ page }) => {
  await page.goto('/');

  await page.getByPlaceholder('Enter username').fill(DEV_USER.username);
  await page.getByPlaceholder('Enter password').fill(DEV_USER.password);
  await page.getByRole('button', { name: /sign in/i }).click();

  // Successful login shows the primary navigation.
  await expect(page.getByRole('link', { name: /review queue/i })).toBeVisible();

  await page.getByRole('link', { name: /review queue/i }).click();
  await expect(page.getByRole('heading', { name: /review queue/i })).toBeVisible();
});

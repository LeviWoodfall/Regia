import '@testing-library/jest-dom/vitest';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '../SettingsPage';

const apiMocks = {
  getStatus: vi.fn(),
  setupMasterPassword: vi.fn(),
  apiUnlock: vi.fn(),
  apiLock: vi.fn(),
  getAccounts: vi.fn(),
  addAccount: vi.fn(),
  updateAccount: vi.fn(),
  deleteAccount: vi.fn(),
  storeCredentials: vi.fn(),
  getConfig: vi.fn(),
  updateConfig: vi.fn(),
  getCloudProviders: vi.fn(),
  getCloudConnections: vi.fn(),
  createCloudConnection: vi.fn(),
  deleteCloudConnection: vi.fn(),
  startOAuth2Flow: vi.fn(),
  getEmailProviders: vi.fn(),
  getRules: vi.fn(),
  createRule: vi.fn(),
  updateRule: vi.fn(),
  deleteRule: vi.fn(),
  getRuleFields: vi.fn(),
  getCloudMode: vi.fn(),
  refreshAllAttachments: vi.fn(),
  refreshAllStatus: vi.fn(),
  schedulerStart: vi.fn(),
  schedulerStop: vi.fn(),
  schedulerStatus: vi.fn(),
};

vi.mock('../../lib/api', () => ({
  __esModule: true,
  ...apiMocks,
}));

vi.mock('../../lib/theme', () => ({
  __esModule: true,
  useTheme: () => ({
    theme: 'sunset',
    setTheme: vi.fn(),
    themes: ['sunset', 'ocean'],
    metadata: {
      sunset: { label: 'Sunset', description: '', swatches: ['#fff'] },
      ocean: { label: 'Ocean', description: '', swatches: ['#fff'] },
    },
  }),
}));

const resolvedVoid = Promise.resolve({ data: {} });

beforeEach(() => {
  Object.values(apiMocks).forEach(fn => fn.mockReset?.());
  apiMocks.getStatus.mockResolvedValue({ data: { initialized: true, unlocked: true } });
  apiMocks.getAccounts.mockResolvedValue({ data: { accounts: [] } });
  apiMocks.getConfig.mockResolvedValue({ data: { scheduler: { enabled: true } } });
  apiMocks.getCloudProviders.mockResolvedValue({ data: { providers: [] } });
  apiMocks.getCloudConnections.mockResolvedValue({ data: { connections: [] } });
  apiMocks.getEmailProviders.mockResolvedValue({ data: { providers: [] } });
  apiMocks.getRules.mockResolvedValue({ data: { rules: [] } });
  apiMocks.getRuleFields.mockResolvedValue({ data: {} });
  apiMocks.getCloudMode.mockResolvedValue({ data: {} });
  apiMocks.schedulerStatus.mockResolvedValue({ data: { running: false, jobs: [] } });
  apiMocks.createCloudConnection.mockReturnValue(resolvedVoid);
  apiMocks.deleteCloudConnection.mockReturnValue(resolvedVoid);
  apiMocks.startOAuth2Flow.mockResolvedValue({ data: { url: 'http://example.com' } });
  apiMocks.addAccount.mockReturnValue(resolvedVoid);
  apiMocks.updateAccount.mockReturnValue(resolvedVoid);
  apiMocks.deleteAccount.mockReturnValue(resolvedVoid);
  apiMocks.storeCredentials.mockReturnValue(resolvedVoid);
  apiMocks.updateConfig.mockReturnValue(resolvedVoid);
  apiMocks.createRule.mockReturnValue(resolvedVoid);
  apiMocks.updateRule.mockReturnValue(resolvedVoid);
  apiMocks.deleteRule.mockReturnValue(resolvedVoid);
  apiMocks.schedulerStart.mockResolvedValue({});
  apiMocks.schedulerStop.mockResolvedValue({});
  apiMocks.refreshAllAttachments.mockReturnValue(resolvedVoid);
  apiMocks.refreshAllStatus.mockResolvedValue({ data: {} });
  apiMocks.setupMasterPassword.mockReturnValue(resolvedVoid);
  apiMocks.apiUnlock.mockReturnValue(resolvedVoid);
  apiMocks.apiLock.mockReturnValue(resolvedVoid);
});

describe('SettingsPage Scheduler Tab', () => {
  it('invokes schedulerStart when clicking Start Poller', async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    const schedulerTab = await screen.findByRole('button', { name: /scheduler/i });
    await user.click(schedulerTab);

    await waitFor(() => expect(apiMocks.schedulerStatus).toHaveBeenCalled());

    const startButton = await screen.findByRole('button', { name: /start poller/i });
    await user.click(startButton);

    expect(apiMocks.schedulerStart).toHaveBeenCalledTimes(1);
  });

  it('renders scheduler jobs returned from API', async () => {
    apiMocks.schedulerStatus.mockResolvedValueOnce({
      data: {
        running: true,
        jobs: [
          {
            id: 'job-1',
            name: 'Fetch Primary',
            status: 'running',
            account_id: 'acct-1',
            run_count: 3,
            last_run_at: '2024-01-01T00:00:00Z',
          },
        ],
      },
    });

    render(<SettingsPage />);

    const schedulerTab = await screen.findByRole('button', { name: /scheduler/i });
    await userEvent.click(schedulerTab);

    await screen.findByText(/fetch primary/i);
    expect(screen.getByText(/account: acct-1/i)).toBeInTheDocument();
    expect(screen.getByText(/runs: 3/i)).toBeInTheDocument();
  });
});

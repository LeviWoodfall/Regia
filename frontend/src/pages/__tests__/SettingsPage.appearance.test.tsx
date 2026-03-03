import '@testing-library/jest-dom/vitest';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '../SettingsPage';

const apiMocks = vi.hoisted(() => ({
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
}));

const setThemeMock = vi.fn();

vi.mock('../../lib/api', () => ({
  __esModule: true,
  ...apiMocks,
}));

vi.mock('../../lib/theme', () => ({
  __esModule: true,
  useTheme: () => ({
    theme: 'sunset',
    setTheme: setThemeMock,
    themes: ['sunset', 'ocean'],
    metadata: {
      sunset: { label: 'Sunset', description: 'Warm oranges', swatches: ['#f8c8a0'] },
      ocean: { label: 'Ocean', description: 'Cool blues', swatches: ['#6ec1ff'] },
    },
  }),
}));

const resolvedVoid = Promise.resolve({ data: {} });

beforeEach(() => {
  Object.values(apiMocks).forEach(fn => fn.mockReset?.());
  setThemeMock.mockReset();
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

describe('SettingsPage Appearance Tab', () => {
  it('shows active theme chip and badge', async () => {
    render(<SettingsPage />);

    const appearanceTab = await screen.findByRole('button', { name: /appearance/i });
    await userEvent.click(appearanceTab);

    await screen.findByText(/Active theme:/i);
    expect(screen.getAllByText(/^Active$/i)[0]).toBeInTheDocument();
  });

  it('invokes setTheme when selecting another palette', async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    const appearanceTab = await screen.findByRole('button', { name: /appearance/i });
    await user.click(appearanceTab);

    const oceanCard = await screen.findByRole('button', { name: /Ocean/i });
    await user.click(oceanCard);

    expect(setThemeMock).toHaveBeenCalledWith('ocean');
  });
});

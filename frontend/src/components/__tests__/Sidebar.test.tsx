import '@testing-library/jest-dom/vitest';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Sidebar from '../Sidebar';

const setThemeMock = vi.fn();
const logoutMock = vi.fn();

vi.mock('../../lib/theme', () => ({
  __esModule: true,
  useTheme: () => ({
    theme: 'sunset',
    setTheme: setThemeMock,
    themes: ['sunset', 'ocean'],
    metadata: {
      sunset: { label: 'Sunset' },
      ocean: { label: 'Ocean' },
    },
  }),
}));

vi.mock('../../lib/auth', () => ({
  __esModule: true,
  useAuth: () => ({
    user: { display_name: 'Test User', username: 'test' },
    logout: logoutMock,
  }),
}));

describe('Sidebar', () => {
  beforeEach(() => {
    setThemeMock.mockClear();
  });

  it('cycles theme to the next palette when clicking the toggle', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    await user.click(screen.getByRole('button', { name: /theme/i }));
    expect(setThemeMock).toHaveBeenCalledWith('ocean');
  });
});

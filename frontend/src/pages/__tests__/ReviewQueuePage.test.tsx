import '@testing-library/jest-dom/vitest';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ReviewQueuePage from '../ReviewQueuePage';

const apiMocks = {
  getReviewQueue: vi.fn(),
  approveEmail: vi.fn(),
  rejectEmail: vi.fn(),
  archiveEmail: vi.fn(),
  captureLink: vi.fn(),
};

vi.mock('../../lib/api', () => ({
  __esModule: true,
  ...apiMocks,
}));

vi.mock('../../lib/utils', () => ({
  formatDateTime: (value: string) => value,
  truncate: (value: string) => value,
}));

const queuePayload = {
  data: {
    items: [
      {
        id: 1,
        subject: 'Invoice 2024-01',
        sender_name: 'Acme Billing',
        sender_email: 'billing@acme.test',
        date_sent: '2024-01-01T00:00:00Z',
        invoice_links: ['https://example.com/invoice.pdf'],
        body_html: '<p>Invoice body</p>',
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
  },
};

beforeEach(() => {
  Object.values(apiMocks).forEach(fn => fn.mockReset?.());
  apiMocks.getReviewQueue.mockResolvedValue(queuePayload);
  apiMocks.approveEmail.mockResolvedValue({});
  apiMocks.rejectEmail.mockResolvedValue({});
  apiMocks.archiveEmail.mockResolvedValue({});
  apiMocks.captureLink.mockResolvedValue({});
});

describe('ReviewQueuePage', () => {
  it('renders queue items and shows detail when selecting a row', async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);

    await waitFor(() => expect(apiMocks.getReviewQueue).toHaveBeenCalled());
    const row = await screen.findByText('Invoice 2024-01');
    await user.click(row);

    expect(await screen.findByText(/Approve/)).toBeInTheDocument();
    expect(screen.getByText(/Acme Billing/)).toBeInTheDocument();
  });

  it('calls approveEmail when approving selected item', async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);

    const row = await screen.findByText('Invoice 2024-01');
    await user.click(row);

    const approveButton = await screen.findByRole('button', { name: /approve/i });
    await user.click(approveButton);

    expect(apiMocks.approv
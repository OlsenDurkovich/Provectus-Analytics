import { render, screen, fireEvent } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { RebuildConfirmDialog } from './RebuildConfirmDialog';

function setup(props = {}) {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  render(<RebuildConfirmDialog open onConfirm={onConfirm} onCancel={onCancel} {...props} />);
  return { onConfirm, onCancel };
}

test('renders nothing when closed', () => {
  const { container } = render(
    <RebuildConfirmDialog open={false} onConfirm={() => {}} onCancel={() => {}} />,
  );
  expect(container.firstChild).toBeNull();
});

test('confirm is disabled until REBUILD is typed', () => {
  const { onConfirm } = setup();
  const btn = screen.getByRole('button', { name: /rebuild database/i });
  expect(btn).toBeDisabled();
  // wrong text stays disabled
  fireEvent.change(screen.getByPlaceholderText('REBUILD'), { target: { value: 'rebuil' } });
  expect(btn).toBeDisabled();
  // correct (case-insensitive) arms it
  fireEvent.change(screen.getByPlaceholderText('REBUILD'), { target: { value: 'rebuild' } });
  expect(btn).toBeEnabled();
  fireEvent.click(btn);
  expect(onConfirm).toHaveBeenCalledTimes(1);
});

test('cancel fires onCancel', () => {
  const { onCancel } = setup();
  fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
  expect(onCancel).toHaveBeenCalledTimes(1);
});

test('while pending the confirm button shows progress and is disabled', () => {
  setup({ pending: true });
  const btn = screen.getByRole('button', { name: /rebuilding/i });
  expect(btn).toBeDisabled();
});

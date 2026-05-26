import { renderHook, act } from '@testing-library/react';
import { beforeEach } from 'vitest';
import { useTheme } from './useTheme';
import { useRange } from './useRange';

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
});

test('useTheme defaults to dark', () => {
  const { result } = renderHook(() => useTheme());
  expect(result.current.theme).toBe('dark');
});

test('useTheme toggles + persists', () => {
  const { result } = renderHook(() => useTheme());
  act(() => result.current.toggle());
  expect(result.current.theme).toBe('light');
  expect(localStorage.getItem('pv-theme')).toBe('light');
  expect(document.documentElement.getAttribute('data-theme')).toBe('light');
});

test('useRange defaults to 12mo', () => {
  const { result } = renderHook(() => useRange());
  expect(result.current.range).toBe('12mo');
});

test('useRange respects initial', () => {
  const { result } = renderHook(() => useRange('30d'));
  expect(result.current.range).toBe('30d');
});

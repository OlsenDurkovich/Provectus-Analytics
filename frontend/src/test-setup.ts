import '@testing-library/jest-dom';

// jsdom doesn't ship ResizeObserver — chart components use it for responsive SVGs.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as { ResizeObserver?: typeof ResizeObserverStub }).ResizeObserver = ResizeObserverStub;

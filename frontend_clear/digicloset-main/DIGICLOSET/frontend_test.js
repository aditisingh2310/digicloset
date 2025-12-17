// tests/frontend_test.js
import { render, screen } from '@testing-library/react';
import App from '../frontend/src/App';

test('renders main app component', () => {
  render(<App />);
  const linkElement = screen.getByText(/digicloset/i);
  expect(linkElement).toBeInTheDocument();
});
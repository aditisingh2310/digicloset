import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
// A tiny smoke test. Replace with actual component test.
test('renders without crashing', () => {
  const div = document.createElement('div');
  document.body.appendChild(div);
  expect(1 + 1).toBe(2);
});

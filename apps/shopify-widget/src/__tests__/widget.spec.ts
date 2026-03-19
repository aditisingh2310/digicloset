import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ShopifyTryOnWidget } from '../index';

describe('ShopifyTryOnWidget', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="tryon-widget-container"></div>
      <div id="outside"></div>
    `;
    delete (window as any).ShopifyTryOnWidget;
    delete (window as any).productId;
    vi.restoreAllMocks();
  });

  it('mounts into the container and exposes the window API', async () => {
    const widget = new ShopifyTryOnWidget({
      containerId: 'tryon-widget-container',
      productId: 'p-1',
      debug: false,
    });

    widget.init();
    document.dispatchEvent(new Event('DOMContentLoaded'));
    await new Promise((resolve) => setTimeout(resolve, 0));

    const api = (window as any).ShopifyTryOnWidget;
    expect(api).toBeTruthy();
    expect(api.getConfig().productId).toBe('p-1');

    const container = document.getElementById('tryon-widget-container')!;
    expect(container.querySelector('.tryon-widget')).toBeTruthy();
    expect(document.getElementById('outside')!.childElementCount).toBe(0);

    api.setVisible(false);
    expect(container.style.display).toBe('none');

    api.unmount();
    expect(container.querySelector('.tryon-widget')).toBeNull();
  });
});

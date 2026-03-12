/**
 * Shopify Try-On Widget Entry Point
 * 
 * This script:
 * 1. Detects when product page is ready
 * 2. Finds the widget container element
 * 3. Initializes the React widget
 * 4. Provides window API for Shopify theme integration
 */

import ReactDOM from 'react-dom/client';
import TryOnWidget from './components/TryOnWidget';
import './styles/globals.css';

// ==================== INITIALIZATION ====================

interface WidgetConfig {
  containerId?: string;
  productId?: string;
  shopifyTheme?: string;
  debug?: boolean;
}

class ShopifyTryOnWidget {
  private config: WidgetConfig;
  private root: ReturnType<typeof ReactDOM.createRoot> | null = null;

  constructor(config: WidgetConfig = {}) {
    this.config = {
      containerId: 'tryon-widget-container',
      debug: false,
      ...config
    };

    this.log('Initializing Shopify Try-On Widget', this.config);
  }

  /**
   * Initialize widget when DOM is ready
   */
  public init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.mount());
    } else {
      this.mount();
    }
  }

  /**
   * Mount React component to DOM
   */
  private mount() {
    const container = document.getElementById(this.config.containerId!);

    if (!container) {
      this.error(
        `Container element with ID "${this.config.containerId}" not found`
      );
      return;
    }

    try {
      // Create root and render
      const root = ReactDOM.createRoot(container);
      root.render(
        <>
          <TryOnWidget />
        </>
      );
      this.root = root;

      // Store product ID in window for widget access
      if (this.config.productId) {
        (window as any).productId = this.config.productId;
      }

      // Expose API for theme integration
      this.exposeAPI();

      this.log('Widget mounted successfully');
    } catch (err) {
      this.error('Failed to mount widget:', err);
    }
  }

  /**
   * Expose widget API on window object
   */
  private exposeAPI() {
    (window as any).ShopifyTryOnWidget = {
      version: '1.0.0',
      config: this.config,
      
      /**
       * Unmount the widget
       */
      unmount: () => {
        if (this.root) {
          this.root.unmount();
          this.log('Widget unmounted');
        }
      },

      /**
       * Get current configuration
       */
      getConfig: () => this.config,

      /**
       * Update configuration
       */
      setConfig: (newConfig: Partial<WidgetConfig>) => {
        this.config = { ...this.config, ...newConfig };
        this.log('Configuration updated', this.config);
      },

      /**
       * Show/hide widget
       */
      setVisible: (visible: boolean) => {
        const container = document.getElementById(this.config.containerId!);
        if (container) {
          container.style.display = visible ? 'block' : 'none';
          this.log(`Widget visibility: ${visible}`);
        }
      },

      /**
       * Log message
       */
      log: (...args: any[]) => this.log(...args),

      /**
       * Enable debug mode
       */
      enableDebug: () => {
        this.config.debug = true;
        this.log('Debug mode enabled');
      },

      /**
       * Disable debug mode
       */
      disableDebug: () => {
        this.config.debug = false;
        this.log('Debug mode disabled');
      }
    };

    this.log('API exposed on window.ShopifyTryOnWidget');
  }

  /**
   * Logging utility
   */
  private log(...args: any[]) {
    if (this.config.debug) {
      console.log('[ShopifyTryOnWidget]', ...args);
    }
  }

  /**
   * Error logging utility
   */
  private error(...args: any[]) {
    console.error('[ShopifyTryOnWidget]', ...args);
  }
}

// ==================== AUTO-INITIALIZATION ====================

// Check if we should auto-initialize
if (document.currentScript) {
  const script = document.currentScript as HTMLScriptElement;
  
  // Parse configuration from data attributes
  const config: WidgetConfig = {
    containerId: script.dataset.container || 'tryon-widget-container',
    productId: script.dataset.productId,
    shopifyTheme: script.dataset.theme,
    debug: script.dataset.debug === 'true'
  };

  // Initialize widget
  const widget = new ShopifyTryOnWidget(config);
  widget.init();
}

// ==================== MANUAL INITIALIZATION ====================

// Export for manual initialization if needed
export { ShopifyTryOnWidget as default };
export { ShopifyTryOnWidget };

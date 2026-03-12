# Shopify Virtual Try-On Widget

Professional virtual try-on widget for Shopify product pages. Allows customers to see how garments look on them before purchase.

## Features

- 🎬 Real-time virtual try-on generation
- 📱 Mobile-responsive design  
- ⚡ Fast async polling for results
- 🎨 Customizable styling
- 🔒 Secure OAuth integration
- 💳 Built-in billing management
- 📊 Analytics and metrics
- ♿ Accessibility-first design

## Installation

### 1. Build the Widget

```bash
cd apps/shopify-widget
npm install
npm run build
```

This generates:
- `dist/shopify-tryon-widget.js` - UMD bundle for Shopify
- `dist/shopify-tryon-widget.es.js` - ES module
- `dist/index.d.ts` - TypeScript definitions

### 2. Embed on Shopify Product Page

Add to your Shopify theme's product template (`sections/product-template.liquid` or `product.json`):

```html
<!-- Include React and ReactDOM -->
<script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>

<!-- Widget container -->
<div id="tryon-widget-container"></div>

<!-- Load the widget -->
<script src="https://your-cdn.com/shopify-tryon-widget.js" 
        data-product-id="{{ product.id }}"
        data-container="tryon-widget-container"
        data-debug="false"></script>
```

### 3. Configure Backend URL

The widget expects the backend API at `/api/v1`. Configure your Shopify app to proxy requests to the backend-api service:

```javascript
// In your Shopify app configuration
const backendUrl = 'https://api.yourdomain.com';
// The widget will call: {backendUrl}/api/v1/try-on/generate
```

## Usage

### Automatic Initialization

The widget auto-initializes when the script loads:

```html
<script 
  src="widget.js"
  data-container="tryon-widget-container"
  data-product-id="123456789"
  data-debug="false">
</script>
```

### Manual Initialization

```javascript
import { ShopifyTryOnWidget } from 'shopify-tryon-widget';

const widget = new ShopifyTryOnWidget({
  containerId: 'my-widget-container',
  productId: '123456789',
  debug: true
});

widget.init();
```

### JavaScript API

Access the widget via `window.ShopifyTryOnWidget`:

```javascript
// Show/hide widget
window.ShopifyTryOnWidget.setVisible(true);

// Update config
window.ShopifyTryOnWidget.setConfig({
  productId: 'new-product-id'
});

// Enable debug logging
window.ShopifyTryOnWidget.enableDebug();

// Unmount widget
window.ShopifyTryOnWidget.unmount();
```

## Component Architecture

```
src/
├── components/
│   ├── TryOnWidget.tsx        # Main container
│   ├── ImageUpload.tsx        # Image upload form
│   ├── ProcessingSpinner.tsx  # Loading indicator
│   ├── ResultDisplay.tsx      # Result preview
│   └── TryOnForm.tsx          # Category/size selection
├── hooks/
│   ├── useAuth.ts            # Merchant auth & credits
│   ├── useTryOn.ts           # Try-on API calls
│   └── usePolling.ts         # Async polling utility
├── api/
│   └── client.ts             # Backend API client
├── styles/
│   ├── globals.css           # Global styles
│   ├── TryOnWidget.css       # Container styles
│   ├── ImageUpload.css       # Upload form styles
│   ├── ProcessingSpinner.css # Loading styles
│   ├── ResultDisplay.css     # Result styles
│   └── TryOnForm.css         # Form styles
└── index.tsx                 # Entry point
```

## API Integration

The widget calls the following backend endpoints:

### Try-On Endpoints
- `POST /api/v1/try-on/generate` - Generate new try-on
- `GET /api/v1/try-on/{id}` - Get try-on status/result
- `GET /api/v1/try-on/history` - Get try-on history

### Billing Endpoints
- `GET /api/v1/billing/credits/check` - Check available credits
- `GET /api/v1/billing/history` - Get billing events

### Merchant Endpoints
- `GET /api/v1/merchant/profile` - Get merchant info
- `POST /api/v1/merchant/settings` - Update settings
- `POST /api/v1/merchant/oauth/callback` - OAuth callback

See [Backend API Documentation](../../services/backend-api/README.md) for details.

## Styling

The widget uses CSS variables for theming:

```css
:root {
  --primary: #007bff;
  --success: #28a745;
  --danger: #dc3545;
  --radius-lg: 8px;
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.1);
}
```

Override in your Shopify theme:

```css
:root {
  --primary: #1f2937;
  --success: #10b981;
}
```

## Development

### Local Development

```bash
npm run dev
```

Starts dev server on `http://localhost:3000` with API proxy to `http://localhost:8000`.

### Type Checking

```bash
npm run type-check
```

### Linting

```bash
npm run lint
```

### Testing

```bash
npm test          # Run tests
npm run test:ui   # Interactive test dashboard
```

## Browser Support

- Chrome/Chromium (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Performance

- **Bundle Size**: ~45KB minified (with React)
- **Load Time**: <200ms (excluding React libraries)
- **Polling**: Exponential backoff (2s → 10s max)
- **Timeout**: 300 seconds (150 polls)

## Security

- All API calls use HTTPS
- CORS headers validated on backend
- OAuth tokens secure cookie-based
- Image URLs validated before processing
- Input sanitization on all forms

## Monitoring

The widget emits custom events for analytics:

```javascript
// Listen for events
window.addEventListener('tryon:generated', (e) => {
  console.log('Try-on completed:', e.detail);
  // Send to analytics
  gtag('event', 'tryon_generated', {
    'tryon_id': e.detail.id,
    'duration': e.detail.processingTime
  });
});
```

Available events:
- `tryon:generated` - Try-on completed
- `tryon:addToCart` - Customer clicked Add to Cart
- `tryon:error` - Error occurred
- `tryon:timeout` - Polling timed out

## Troubleshooting

### Widget doesn't appear
- Check browser console for errors
- Verify container element exists: `<div id="tryon-widget-container">`
- Check data attributes on script tag

### API calls fail
- Verify backend URL is correct
- Check CORS configuration on backend
- Verify OAuth token is valid

### Slow performance
- Check image sizes (optimize before upload)
- Verify network latency
- Check backend server load

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md)

## License

MIT - See [LICENSE](../../LICENSE)

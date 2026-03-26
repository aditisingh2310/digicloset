import { ShopifyTryOnWidget } from "./index";

const widget = new ShopifyTryOnWidget({
  containerId: "tryon-widget-container",
  productId: "dev-product-123",
  debug: true,
});

widget.init();

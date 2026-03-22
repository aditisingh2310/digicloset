import crypto from "crypto";
import {
  getCustomerData,
  deleteCustomerData,
  deleteShopData,
} from "./gdpr.service.js";

// 🔐 Verify Shopify webhook
const verifyWebhook = (req) => {
  const hmac = req.headers["x-shopify-hmac-sha256"];
  const body = req.rawBody; // make sure rawBody is available

  const hash = crypto
    .createHmac("sha256", process.env.SHOPIFY_API_SECRET)
    .update(body, "utf8")
    .digest("base64");

  return hash === hmac;
};

export const handleWebhook = async (req, res) => {
  try {
    if (!verifyWebhook(req)) {
      return res.status(401).send("Invalid webhook");
    }

    const topic = req.headers["x-shopify-topic"];
    const shop = req.headers["x-shopify-shop-domain"];
    const body = JSON.parse(req.rawBody);

    console.log("Webhook received:", topic);

    switch (topic) {
      /**
       * 🔴 CUSTOMER DATA REQUEST
       */
      case "customers/data_request": {
        const data = await getCustomerData(shop, body.customer.id);

        console.log("GDPR DATA REQUEST:", data);
        break;
      }

      /**
       * 🔴 CUSTOMER REDACT
       */
      case "customers/redact": {
        await deleteCustomerData(shop, body.customer.id);

        console.log(`Customer ${body.customer.id} deleted`);
        break;
      }

      /**
       * 🔴 SHOP REDACT
       */
      case "shop/redact": {
        await deleteShopData(shop);

        console.log(`Shop ${shop} data deleted`);
        break;
      }

      default:
        console.log(`Unhandled webhook topic: ${topic}`);
    }

    return res.status(200).send("OK");
  } catch (err) {
    console.error("Webhook error:", err);
    return res.status(500).send("Webhook processing failed");
  }
};

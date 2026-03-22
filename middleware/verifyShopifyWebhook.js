import crypto from "crypto";

export const verifyShopifyWebhook = (req, res, next) => {
  try {
    const hmac = req.get("X-Shopify-Hmac-Sha256");
    const body = JSON.stringify(req.body);

    const generatedHash = crypto
      .createHmac("sha256", process.env.SHOPIFY_WEBHOOK_SECRET)
      .update(body, "utf8")
      .digest("base64");

    if (generatedHash !== hmac) {
      return res.status(401).send("Webhook verification failed");
    }

    next();
  } catch (err) {
    console.error("Webhook verification error:", err);
    return res.status(500).send("Webhook error");
  }
};

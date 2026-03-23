# DigiCloset Privacy Policy

Last updated: March 23, 2026

DigiCloset provides Shopify merchants with virtual try-on, product presentation, and related merchant tooling. This policy describes how DigiCloset handles merchant and storefront data when the app is installed or used.

## Information We Process

DigiCloset may process:

- Merchant account and store details such as shop domain, install state, and app configuration.
- Shopify access tokens and session data required to operate the app.
- Merchant billing, usage, and support records.
- Product metadata, product imagery, and generated try-on assets needed to provide the service.
- Operational logs, security telemetry, and webhook delivery metadata.
- Feedback submitted through the app or support channels.

The active DigiCloset backend is designed primarily around merchant and store data. It does not maintain a dedicated customer profile store in its primary application database.

## How We Use Information

We use processed information to:

- authenticate and operate the Shopify app;
- generate virtual try-on and related AI-assisted experiences;
- measure usage, billing, and service health;
- secure the service, prevent abuse, and investigate incidents;
- provide merchant support and improve the product.

## Sharing

DigiCloset may share data with:

- Shopify, when required to provide the installed app experience;
- infrastructure, hosting, monitoring, storage, and processing providers acting on DigiCloset's behalf;
- legal or regulatory authorities when required by law.

DigiCloset does not sell merchant personal data.

## Retention and Deletion

- Merchant-scoped operational data is retained only as long as needed to provide the service, meet legal obligations, and protect the platform.
- On `app/uninstalled` and `shop/redact`, DigiCloset is designed to revoke tokens, revoke sessions, and remove merchant-scoped records tied to the shop.
- `customers/data_request` and `customers/redact` requests are recorded for compliance handling. Because the active backend does not maintain a dedicated customer profile store, these requests are reviewed against the data that is actually held before a response is completed.

## Your Rights and Requests

Merchants may request access, correction, or deletion of merchant-scoped data. Shopify GDPR webhooks are used to receive platform-issued compliance requests.

Privacy and data handling questions may be sent to:

- `support@digicloset.ai`

## Security

DigiCloset uses server-side token storage, request signing checks, session revocation on uninstall, and structured logging with sensitive-value redaction to reduce data exposure risk.

## Changes

DigiCloset may update this policy as the service, infrastructure, or legal requirements change. The current version will be posted at the in-app privacy route.

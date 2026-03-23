import {
  Badge,
  BlockStack,
  Button,
  Card,
  InlineStack,
  Layout,
  Page,
  Text,
} from "@shopify/polaris";

const PLANS = [
  {
    name: "Starter",
    price: "$9",
    cadence: "/month",
    caption: "Best for early pilots and catalog testing.",
    features: [
      "Up to 150 try-ons",
      "Email support",
      "Launch checklist guidance",
    ],
  },
  {
    name: "Growth",
    price: "$29",
    cadence: "/month",
    caption: "For stores making try-on part of the main PDP journey.",
    features: [
      "Up to 750 try-ons",
      "Priority support",
      "Quality review sessions",
    ],
    featured: true,
  },
  {
    name: "Scale",
    price: "$79",
    cadence: "/month",
    caption: "For high-volume catalogs with active optimization loops.",
    features: [
      "Up to 3,000 try-ons",
      "Dedicated success support",
      "Custom rollout planning",
    ],
  },
];

export default function Pricing() {
  return (
    <Page title="Pricing">
      <Layout>
        <Layout.Section>
          <div className="dc-page">
            <Card>
              <div className="dc-surface-card">
                <BlockStack gap="300">
                  <InlineStack align="space-between" blockAlign="center">
                    <BlockStack gap="200">
                      <Text as="p" variant="bodySm" tone="subdued" className="dc-kicker">
                        Transparent pricing
                      </Text>
                      <Text as="h2" variant="headingXl">
                        Choose the pace that matches your rollout.
                      </Text>
                    </BlockStack>
                    <Badge tone="success">7-day free trial</Badge>
                  </InlineStack>

                  <Text as="p" variant="bodyMd" tone="subdued">
                    Start lean, prove conversion impact on a focused set of products, and scale once the widget earns its place in your purchase funnel.
                  </Text>
                </BlockStack>
              </div>
            </Card>

            <div className="dc-pricing-grid">
              {PLANS.map((plan) => (
                <Card key={plan.name}>
                  <div
                    className={`dc-plan-card${plan.featured ? " dc-plan-card--featured" : ""}`}
                  >
                    <BlockStack gap="400">
                      <InlineStack align="space-between" blockAlign="center">
                        <Text as="h3" variant="headingLg">
                          {plan.name}
                        </Text>
                        {plan.featured ? <Badge tone="success">Most popular</Badge> : null}
                      </InlineStack>

                      <div className="dc-price">
                        <strong>{plan.price}</strong>
                        <Text as="span" variant="bodyMd" tone="subdued">
                          {plan.cadence}
                        </Text>
                      </div>

                      <Text as="p" variant="bodyMd" tone="subdued">
                        {plan.caption}
                      </Text>

                      <ul className="dc-bullet-list">
                        {plan.features.map((feature) => (
                          <li key={feature}>
                            <Text as="p" variant="bodyMd">
                              {feature}
                            </Text>
                          </li>
                        ))}
                      </ul>

                      <Button variant={plan.featured ? "primary" : "secondary"}>
                        Start free trial
                      </Button>
                    </BlockStack>
                  </div>
                </Card>
              ))}
            </div>

            <Card>
              <div className="dc-support-card">
                <BlockStack gap="200">
                  <Text as="h3" variant="headingLg">
                    Not sure which plan fits?
                  </Text>
                  <Text as="p" variant="bodyMd" tone="subdued">
                    If you are still validating widget placement, start smaller. If your store already has meaningful PDP traffic, Growth usually gives the best room to learn fast.
                  </Text>
                </BlockStack>
              </div>
            </Card>
          </div>
        </Layout.Section>
      </Layout>
    </Page>
  );
}

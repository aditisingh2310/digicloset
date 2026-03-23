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
import { useNavigate } from "react-router-dom";

const STEPS = [
  {
    title: "Install and verify the embed",
    body: "Confirm the widget appears on your product page template and sits near your buying actions.",
    status: "Ready",
  },
  {
    title: "Choose launch products",
    body: "Prioritize hero products with clean photography and consistent garment framing.",
    status: "Recommended",
  },
  {
    title: "Approve your first outputs",
    body: "Review early generations so the AI can learn what looks on-brand before shoppers see it.",
    status: "Important",
  },
];

export default function Onboarding() {
  const navigate = useNavigate();

  return (
    <Page title="Launch onboarding">
      <Layout>
        <Layout.Section>
          <div className="dc-page">
            <Card>
              <div className="dc-surface-card">
                <BlockStack gap="400">
                  <InlineStack align="space-between" blockAlign="center">
                    <BlockStack gap="200">
                      <Text as="p" variant="bodySm" tone="subdued" className="dc-kicker">
                        Merchant setup
                      </Text>
                      <Text as="h2" variant="headingXl">
                        Build confidence before you send traffic into try-on.
                      </Text>
                      <Text as="p" variant="bodyMd" tone="subdued">
                        A smooth launch comes from tight placement, clean source imagery, and a short review loop on your first generated looks.
                      </Text>
                    </BlockStack>
                    <Badge tone="info">About 15 minutes</Badge>
                  </InlineStack>

                  <div className="dc-inline-actions">
                    <Button variant="primary" onClick={() => navigate("/")}>
                      Back to overview
                    </Button>
                    <Button onClick={() => navigate("/pricing")}>
                      See plans
                    </Button>
                  </div>
                </BlockStack>
              </div>
            </Card>

            <div className="dc-stat-grid">
              {STEPS.map((step, index) => (
                <Card key={step.title}>
                  <div className="dc-surface-card">
                    <BlockStack gap="300">
                      <InlineStack align="space-between">
                        <Text as="h3" variant="headingMd">
                          Step {index + 1}
                        </Text>
                        <Badge>{step.status}</Badge>
                      </InlineStack>
                      <Text as="p" variant="headingSm">
                        {step.title}
                      </Text>
                      <Text as="p" variant="bodyMd" tone="subdued">
                        {step.body}
                      </Text>
                    </BlockStack>
                  </div>
                </Card>
              ))}
            </div>

            <Card>
              <div className="dc-support-card">
                <BlockStack gap="300">
                  <Text as="h3" variant="headingLg">
                    Recommended launch sequence
                  </Text>
                  <ul className="dc-bullet-list">
                    <li>
                      <Text as="p" variant="headingSm">
                        1. Pilot with 10 to 20 products
                      </Text>
                      <Text as="p" variant="bodySm" tone="subdued">
                        Keep the first batch small enough to QA thoroughly.
                      </Text>
                    </li>
                    <li>
                      <Text as="p" variant="headingSm">
                        2. Review output quality twice a day
                      </Text>
                      <Text as="p" variant="bodySm" tone="subdued">
                        The first 48 hours tell you whether source imagery or prompt settings need tuning.
                      </Text>
                    </li>
                    <li>
                      <Text as="p" variant="headingSm">
                        3. Expand once results feel consistent
                      </Text>
                      <Text as="p" variant="bodySm" tone="subdued">
                        Scale to the rest of the catalog only after your hero products feel dependable.
                      </Text>
                    </li>
                  </ul>
                </BlockStack>
              </div>
            </Card>
          </div>
        </Layout.Section>
      </Layout>
    </Page>
  );
}

import {
  Badge,
  BlockStack,
  Button,
  Card,
  InlineStack,
  Layout,
  Page,
  ProgressBar,
  Text,
} from "@shopify/polaris";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Loading from "../components/Loading";

const METRICS = [
  { label: "Products ready", value: "18", detail: "6 still need clean imagery" },
  { label: "Median render time", value: "41s", detail: "8s faster than last week" },
  { label: "Projected lift", value: "+12%", detail: "Based on early pilot stores" },
];

const CHECKLIST = [
  {
    title: "Connect your catalog",
    body: "Import your top-selling products first so the AI can learn from your strongest assortment.",
  },
  {
    title: "Place the widget on PDPs",
    body: "Keep the try-on entry within the add-to-cart zone so shoppers notice it before they bounce.",
  },
  {
    title: "Review first generation batch",
    body: "Approve your first looks manually to tighten quality and keep the recommendations on-brand.",
  },
];

export default function Home() {
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 500);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return <Loading />;
  }

  return (
    <Page title="DigiCloset command center">
      <Layout>
        <Layout.Section>
          <div className="dc-page">
            <Card>
              <div className="dc-hero-card">
                <BlockStack gap="500">
                  <BlockStack gap="200">
                    <Text as="p" variant="bodySm" className="dc-kicker">
                      Virtual try-on readiness
                    </Text>
                    <InlineStack align="space-between" blockAlign="start" gap="400">
                      <BlockStack gap="300">
                        <Text as="h2" variant="heading2xl">
                          Launch a try-on flow that feels premium from day one.
                        </Text>
                        <Text as="p" variant="bodyMd">
                          Your storefront foundations are in place. The next win is tightening setup, surfacing the widget in the right moments, and making your first live results feel trustworthy.
                        </Text>
                      </BlockStack>
                      <Badge tone="attention">Guided launch mode</Badge>
                    </InlineStack>
                  </BlockStack>

                  <div className="dc-hero-pills">
                    <span className="dc-pill">Fastest gains on hero SKUs</span>
                    <span className="dc-pill">Best results with 3+ clean product angles</span>
                    <span className="dc-pill">Support response under 1 business day</span>
                  </div>

                  <div className="dc-inline-actions">
                    <Button variant="primary" onClick={() => navigate("/onboarding")}>
                      Finish onboarding
                    </Button>
                    <Button onClick={() => navigate("/pricing")}>
                      Review plan options
                    </Button>
                  </div>
                </BlockStack>
              </div>
            </Card>

            <div className="dc-stat-grid">
              {METRICS.map((metric) => (
                <Card key={metric.label}>
                  <div className="dc-stat-card">
                    <BlockStack gap="200">
                      <Text as="p" variant="bodySm" tone="subdued">
                        {metric.label}
                      </Text>
                      <p className="dc-stat-value">{metric.value}</p>
                      <Text as="p" variant="bodySm" tone="subdued">
                        {metric.detail}
                      </Text>
                    </BlockStack>
                  </div>
                </Card>
              ))}
            </div>

            <Layout>
              <Layout.Section>
                <Card>
                  <div className="dc-surface-card">
                    <BlockStack gap="400">
                      <InlineStack align="space-between">
                        <Text as="h3" variant="headingLg">
                          Go-live checklist
                        </Text>
                        <Badge tone="success">67% complete</Badge>
                      </InlineStack>

                      <ProgressBar progress={67} size="small" />

                      <ul className="dc-checklist">
                        {CHECKLIST.map((item, index) => (
                          <li key={item.title}>
                            <Text as="p" variant="headingSm">
                              {index + 1}. {item.title}
                            </Text>
                            <Text as="p" variant="bodyMd" tone="subdued">
                              {item.body}
                            </Text>
                          </li>
                        ))}
                      </ul>
                    </BlockStack>
                  </div>
                </Card>
              </Layout.Section>

              <Layout.Section secondary>
                <BlockStack gap="400">
                  <Card>
                    <div className="dc-surface-card">
                      <BlockStack gap="300">
                        <Text as="h3" variant="headingLg">
                          Quality habits that matter
                        </Text>
                        <ul className="dc-bullet-list">
                          <li>
                            <Text as="p" variant="headingSm">
                              Use clean mannequin-free product imagery
                            </Text>
                            <Text as="p" variant="bodySm" tone="subdued">
                              Strong source photos improve fit realism more than any downstream tweak.
                            </Text>
                          </li>
                          <li>
                            <Text as="p" variant="headingSm">
                              Start with best-selling tops and dresses
                            </Text>
                            <Text as="p" variant="bodySm" tone="subdued">
                              These categories convert quickest and give you better launch feedback.
                            </Text>
                          </li>
                        </ul>
                      </BlockStack>
                    </div>
                  </Card>

                  <Card>
                    <div className="dc-support-card">
                      <BlockStack gap="200">
                        <Text as="h3" variant="headingLg">
                          Need a launch review?
                        </Text>
                        <Text as="p" variant="bodyMd" tone="subdued">
                          We can sanity-check widget placement, product image quality, and first-result consistency before you turn traffic on.
                        </Text>
                        <div className="dc-inline-actions">
                          <Button url="mailto:support@digicloset.ai">Email support</Button>
                        </div>
                      </BlockStack>
                    </div>
                  </Card>
                </BlockStack>
              </Layout.Section>
            </Layout>
          </div>
        </Layout.Section>
      </Layout>
    </Page>
  );
}

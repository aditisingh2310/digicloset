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
import { formatCredits, requestJson } from "../lib/adminApi";

const CHECKLIST = [
  {
    title: "Keep the widget placement close to the buying flow",
    body: "The cleanest outcome is still a small, useful module near product media and add-to-cart.",
  },
  {
    title: "Review the first outputs before scaling traffic",
    body: "A short QA loop on the first try-ons keeps the storefront from feeling experimental.",
  },
  {
    title: "Use live backend state wherever possible",
    body: "This screen should reflect the root app status, widget state, and usage instead of placeholder numbers.",
  },
];

export default function Home() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [billing, setBilling] = useState(null);
  const [error, setError] = useState(null);
  const [toggling, setToggling] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;

    const timer = setTimeout(async () => {
      try {
        const [dashboardPayload, billingPayload] = await Promise.all([
          requestJson("/api/merchant/dashboard"),
          requestJson("/api/billing/status"),
        ]);

        if (!active) {
          return;
        }

        setDashboard(dashboardPayload);
        setBilling(billingPayload);
        setError(null);
      } catch (fetchError) {
        if (!active) {
          return;
        }

        setError(fetchError instanceof Error ? fetchError.message : "Unable to load admin data");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }, 250);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, []);

  const handleWidgetToggle = async () => {
    if (!dashboard) {
      return;
    }

    setToggling(true);

    try {
      const response = await requestJson("/api/merchant/settings", {
        method: "POST",
        body: JSON.stringify({ widget_enabled: !dashboard.widget_enabled }),
      });

      setDashboard((current) =>
        current
          ? {
              ...current,
              widget_enabled: response.widget_enabled,
            }
          : current,
      );
      setError(null);
    } catch (toggleError) {
      setError(toggleError instanceof Error ? toggleError.message : "Unable to update widget state");
    } finally {
      setToggling(false);
    }
  };

  if (loading) {
    return <Loading />;
  }

  const tryonsGenerated = dashboard?.tryons_generated ?? 0;
  const creditsRemaining = billing?.credits ?? 0;
  const history = dashboard?.generation_history ?? [];
  const widgetEnabled = dashboard?.widget_enabled ?? false;
  const planLabel = billing?.plan ? billing.plan[0].toUpperCase() + billing.plan.slice(1) : "Starter";
  const checklistProgress = Math.min(100, 34 + Math.min(tryonsGenerated, 6) * 11 + (widgetEnabled ? 12 : 0));

  return (
    <Page title="DigiCloset command center">
      <Layout>
        <Layout.Section>
          <div className="dc-page">
            <Card>
              <div className="dc-hero-card">
                <div className="dc-hero-grid">
                  <BlockStack gap="500">
                    <BlockStack gap="250">
                      <Text as="p" variant="bodySm" className="dc-kicker">
                        Live admin
                      </Text>
                      <Text as="h2" variant="heading2xl">
                        DigiCloset command center
                      </Text>
                      <Text as="p" variant="bodyMd" className="dc-muted">
                        The admin is now reading the backend state directly. Use this page to watch
                        try-on volume, plan status, and widget availability while you test locally.
                      </Text>
                    </BlockStack>

                    <div className="dc-hero-pills">
                      <span className="dc-pill">{dashboard?.shop || "local-dev.myshopify.com"}</span>
                      <span className="dc-pill">{planLabel} plan</span>
                      <span className="dc-pill">{widgetEnabled ? "Widget enabled" : "Widget paused"}</span>
                    </div>

                    <div className="dc-inline-actions">
                      <Button variant="primary" loading={toggling} onClick={handleWidgetToggle}>
                        {widgetEnabled ? "Pause widget" : "Enable widget"}
                      </Button>
                      <Button onClick={() => navigate("/onboarding")}>Open onboarding</Button>
                      <Button onClick={() => navigate("/pricing")}>Open pricing</Button>
                    </div>

                    {error ? (
                      <Text as="p" variant="bodySm" tone="critical">
                        {error}
                      </Text>
                    ) : null}
                  </BlockStack>

                  <div className="dc-hero-summary">
                    <BlockStack gap="300">
                      <InlineStack align="space-between" blockAlign="center">
                        <Text as="h3" variant="headingMd">
                          Runtime snapshot
                        </Text>
                        <Badge tone={widgetEnabled ? "success" : "attention"}>
                          {widgetEnabled ? "Ready" : "Paused"}
                        </Badge>
                      </InlineStack>
                      <ul className="dc-hero-summary-list">
                        <li>
                          <span>Try-ons generated</span>
                          <strong>{tryonsGenerated}</strong>
                        </li>
                        <li>
                          <span>Credits remaining</span>
                          <strong>{formatCredits(creditsRemaining)}</strong>
                        </li>
                        <li>
                          <span>History entries</span>
                          <strong>{history.length}</strong>
                        </li>
                      </ul>
                    </BlockStack>
                  </div>
                </div>
              </div>
            </Card>

            <div className="dc-preview-grid">
              <Card>
                <div className="dc-preview-card">
                  <BlockStack gap="200">
                    <Text as="p" variant="bodySm" tone="subdued">
                      Store
                    </Text>
                    <Text as="h3" variant="headingMd">
                      {dashboard?.shop || "local-dev.myshopify.com"}
                    </Text>
                    <Text as="p" variant="bodyMd" tone="subdued">
                      Local dev tenant seeded from the root backend.
                    </Text>
                  </BlockStack>
                </div>
              </Card>

              <Card>
                <div className="dc-preview-card">
                  <BlockStack gap="200">
                    <Text as="p" variant="bodySm" tone="subdued">
                      Billing
                    </Text>
                    <Text as="h3" variant="headingMd">
                      {billing?.status || "inactive"}
                    </Text>
                    <Text as="p" variant="bodyMd" tone="subdued">
                      Current plan: {planLabel}
                    </Text>
                  </BlockStack>
                </div>
              </Card>

              <Card>
                <div className="dc-preview-card">
                  <BlockStack gap="200">
                    <Text as="p" variant="bodySm" tone="subdued">
                      Widget
                    </Text>
                    <Text as="h3" variant="headingMd">
                      {widgetEnabled ? "Enabled" : "Paused"}
                    </Text>
                    <Text as="p" variant="bodyMd" tone="subdued">
                      Toggle the live storefront state from this admin.
                    </Text>
                  </BlockStack>
                </div>
              </Card>
            </div>

            <Layout>
              <Layout.Section>
                <Card>
                  <div className="dc-surface-card">
                    <BlockStack gap="400">
                      <InlineStack align="space-between" blockAlign="center">
                        <Text as="h3" variant="headingLg">
                          Go-live checklist
                        </Text>
                        <Badge tone="success">{checklistProgress}% live</Badge>
                      </InlineStack>

                      <ProgressBar progress={checklistProgress} size="small" />

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
                          Recent try-ons
                        </Text>
                        <ul className="dc-bullet-list">
                          {history.length ? (
                            history.slice(0, 3).map((item) => (
                              <li key={item.id}>
                                <Text as="p" variant="headingSm">
                                  {item.product_id || "demo-product"}
                                </Text>
                                <Text as="p" variant="bodySm" tone="subdued">
                                  {item.status} · {item.created_at}
                                </Text>
                              </li>
                            ))
                          ) : (
                            <li>
                              <Text as="p" variant="headingSm">
                                No completed try-ons yet
                              </Text>
                              <Text as="p" variant="bodySm" tone="subdued">
                                Generate one from the widget and it will appear here.
                              </Text>
                            </li>
                          )}
                        </ul>
                      </BlockStack>
                    </div>
                  </Card>

                  <Card>
                    <div className="dc-support-card">
                      <BlockStack gap="200">
                        <Text as="h3" variant="headingLg">
                          What changed
                        </Text>
                        <Text as="p" variant="bodyMd" tone="subdued">
                          This page is no longer static. It now reflects merchant dashboard data,
                          billing state, and widget settings from the root backend.
                        </Text>
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

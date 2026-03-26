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
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { requestJson } from "../lib/adminApi";

export default function Onboarding() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState(null);
  const [toggling, setToggling] = useState(false);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const [statusPayload, dashboardPayload] = await Promise.all([
          requestJson("/api/onboarding/status"),
          requestJson("/api/merchant/dashboard"),
        ]);

        if (!active) {
          return;
        }

        setStatus(statusPayload);
        setDashboard(dashboardPayload);
        setError(null);
      } catch (fetchError) {
        if (!active) {
          return;
        }

        setError(fetchError instanceof Error ? fetchError.message : "Unable to load onboarding data");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      active = false;
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

  const steps = [
    {
      title: "Widget state",
      body: dashboard?.widget_enabled
        ? "The storefront widget is enabled and ready for local PDP testing."
        : "The storefront widget is currently paused. Enable it before storefront review.",
      status: dashboard?.widget_enabled ? "Enabled" : "Pending",
    },
    {
      title: "Plan and trial",
      body: status?.subscription_active
        ? "Billing is active, so the app can move through the rollout without subscription gating."
        : "Billing is not active yet. Use the pricing page to switch or reactivate the local plan.",
      status: status?.subscription_active ? "Active" : "Needs attention",
    },
    {
      title: "Generated output",
      body:
        (dashboard?.generation_history?.length || 0) > 0
          ? `There are ${dashboard.generation_history.length} completed preview(s) recorded for this store.`
          : "No generated previews yet. Run the widget once and the first output will appear in admin history.",
      status: (dashboard?.generation_history?.length || 0) > 0 ? "Ready" : "Waiting",
    },
  ];

  return (
    <Page title="Launch onboarding">
      <Layout>
        <Layout.Section>
          <div className="dc-page">
            <Card>
              <div className="dc-surface-card">
                <BlockStack gap="400">
                  <InlineStack align="space-between" blockAlign="start" gap="300">
                    <BlockStack gap="200">
                      <Text as="p" variant="bodySm" tone="subdued" className="dc-kicker">
                        Merchant setup
                      </Text>
                      <Text as="h2" variant="headingXl">
                        Launch onboarding
                      </Text>
                      <Text as="p" variant="bodyMd" className="dc-muted">
                        This flow is now backed by the root admin APIs. It tells you whether the
                        local widget, billing, and first-run output are actually ready.
                      </Text>
                    </BlockStack>
                    <Badge tone={loading ? "info" : error ? "critical" : "success"}>
                      {loading ? "Loading" : error ? "Action needed" : "Connected"}
                    </Badge>
                  </InlineStack>

                  <div className="dc-inline-actions">
                    <Button variant="primary" onClick={() => navigate("/")}>
                      Back to overview
                    </Button>
                    <Button loading={toggling} onClick={handleWidgetToggle}>
                      {dashboard?.widget_enabled ? "Pause widget" : "Enable widget"}
                    </Button>
                    <Button onClick={() => navigate("/pricing")}>See plans</Button>
                  </div>

                  {error ? (
                    <Text as="p" variant="bodySm" tone="critical">
                      {error}
                    </Text>
                  ) : null}
                </BlockStack>
              </div>
            </Card>

            <div className="dc-stat-grid">
              {steps.map((step, index) => (
                <Card key={step.title}>
                  <div className="dc-step-card">
                    <div className="dc-step-head">
                      <span className="dc-step-number">{index + 1}</span>
                      <Badge>{step.status}</Badge>
                    </div>
                    <Text as="p" variant="headingSm">
                      {step.title}
                    </Text>
                    <Text as="p" variant="bodyMd" tone="subdued">
                      {step.body}
                    </Text>
                  </div>
                </Card>
              ))}
            </div>

            <Layout>
              <Layout.Section>
                <Card>
                  <div className="dc-support-card">
                    <BlockStack gap="300">
                      <Text as="h3" variant="headingLg">
                        Recommended launch sequence
                      </Text>
                      <ul className="dc-bullet-list">
                        <li>
                          <Text as="p" variant="headingSm">
                            1. Turn the widget on and verify the PDP flow
                          </Text>
                          <Text as="p" variant="bodySm" tone="subdued">
                            Make sure the storefront module loads, uploads images, and reaches a completed result.
                          </Text>
                        </li>
                        <li>
                          <Text as="p" variant="headingSm">
                            2. Watch the admin update after the first run
                          </Text>
                          <Text as="p" variant="bodySm" tone="subdued">
                            The overview and onboarding pages should show new try-ons and updated state immediately.
                          </Text>
                        </li>
                        <li>
                          <Text as="p" variant="headingSm">
                            3. Lock the local billing plan you want to simulate
                          </Text>
                          <Text as="p" variant="bodySm" tone="subdued">
                            Use the pricing page to switch the active local plan before more QA and demos.
                          </Text>
                        </li>
                      </ul>
                    </BlockStack>
                  </div>
                </Card>
              </Layout.Section>

              <Layout.Section secondary>
                <Card>
                  <div className="dc-surface-card">
                    <BlockStack gap="300">
                      <Text as="h3" variant="headingLg">
                        Runtime checks
                      </Text>
                      <ul className="dc-bullet-list">
                        <li>
                          <Text as="p" variant="headingSm">
                            Trial days remaining
                          </Text>
                          <Text as="p" variant="bodySm" tone="subdued">
                            {status?.trial_days_remaining ?? 0}
                          </Text>
                        </li>
                        <li>
                          <Text as="p" variant="headingSm">
                            Usage remaining
                          </Text>
                          <Text as="p" variant="bodySm" tone="subdued">
                            {status?.usage_remaining ?? "Unknown"}
                          </Text>
                        </li>
                      </ul>
                    </BlockStack>
                  </div>
                </Card>
              </Layout.Section>
            </Layout>
          </div>
        </Layout.Section>
      </Layout>
    </Page>
  );
}

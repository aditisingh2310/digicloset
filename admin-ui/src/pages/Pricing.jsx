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
import { formatCredits, requestJson } from "../lib/adminApi";

const PLANS = [
  {
    key: "starter",
    name: "Starter",
    price: "$19",
    cadence: "/month",
    caption: "A small local plan for validating placement, quality, and early customer behavior.",
    features: ["Up to 200 try-ons", "Email support", "Basic launch guidance"],
  },
  {
    key: "growth",
    name: "Growth",
    price: "$49",
    cadence: "/month",
    caption: "A balanced plan for stores that want try-on to feel like part of the normal PDP flow.",
    features: ["Up to 1,000 try-ons", "Priority support", "Quality review sessions"],
    featured: true,
  },
  {
    key: "scale",
    name: "Scale",
    price: "$99",
    cadence: "/month",
    caption: "For broader catalogs, heavier traffic, and a more active optimization cycle.",
    features: ["Unlimited try-ons", "Dedicated success support", "Custom rollout planning"],
  },
];

export default function Pricing() {
  const [billing, setBilling] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [busyPlan, setBusyPlan] = useState(null);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const loadData = async () => {
    const [billingPayload, dashboardPayload] = await Promise.all([
      requestJson("/api/billing/status"),
      requestJson("/api/merchant/dashboard"),
    ]);

    setBilling(billingPayload);
    setDashboard(dashboardPayload);
  };

  useEffect(() => {
    let active = true;

    loadData()
      .then(() => {
        if (active) {
          setError(null);
        }
      })
      .catch((fetchError) => {
        if (active) {
          setError(fetchError instanceof Error ? fetchError.message : "Unable to load pricing data");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const handleChoosePlan = async (planKey) => {
    setBusyPlan(planKey);

    try {
      const response = await requestJson(`/api/billing/subscribe?plan=${planKey}`, {
        method: "POST",
      });

      if (response?.confirmation_url) {
        window.location.href = response.confirmation_url;
        return;
      }

      await requestJson(
        `/api/billing/activate?charge_id=${encodeURIComponent(
          response?.subscription_id || `local-${planKey}`,
        )}&shop=${encodeURIComponent(dashboard?.shop || "local-dev.myshopify.com")}`,
      );

      await loadData();
      setMessage(`${planKey[0].toUpperCase()}${planKey.slice(1)} plan is active.`);
      setError(null);
    } catch (planError) {
      setError(planError instanceof Error ? planError.message : "Unable to update plan");
    } finally {
      setBusyPlan(null);
    }
  };

  const currentPlan = billing?.plan || "starter";

  return (
    <Page title="Pricing">
      <Layout>
        <Layout.Section>
          <div className="dc-page">
            <Card>
              <div className="dc-surface-card">
                <BlockStack gap="300">
                  <InlineStack align="space-between" blockAlign="start" gap="300">
                    <BlockStack gap="200">
                      <Text as="p" variant="bodySm" tone="subdued" className="dc-kicker">
                        Transparent pricing
                      </Text>
                      <Text as="h2" variant="headingXl">
                        Live plan controls for local testing.
                      </Text>
                      <Text as="p" variant="bodyMd" className="dc-muted">
                        This page now reads the active billing state from the backend and can switch
                        the local plan without leaving the app.
                      </Text>
                    </BlockStack>
                    <Badge tone={error ? "critical" : "success"}>
                      {error ? "Action needed" : billing?.status || "connected"}
                    </Badge>
                  </InlineStack>

                  <div className="dc-hero-pills">
                    <span className="dc-pill">Current plan: {currentPlan}</span>
                    <span className="dc-pill">Credits: {formatCredits(billing?.credits)}</span>
                    <span className="dc-pill">{dashboard?.shop || "local-dev.myshopify.com"}</span>
                  </div>

                  {message ? (
                    <Text as="p" variant="bodySm" tone="success">
                      {message}
                    </Text>
                  ) : null}
                  {error ? (
                    <Text as="p" variant="bodySm" tone="critical">
                      {error}
                    </Text>
                  ) : null}
                </BlockStack>
              </div>
            </Card>

            <div className="dc-pricing-grid">
              {PLANS.map((plan) => {
                const isCurrent = currentPlan === plan.key;

                return (
                  <Card key={plan.key}>
                    <div className={`dc-plan-card${plan.featured ? " dc-plan-card--featured" : ""}`}>
                      <BlockStack gap="400">
                        <InlineStack align="space-between" blockAlign="center">
                          <Text as="h3" variant="headingLg">
                            {plan.name}
                          </Text>
                          {isCurrent ? (
                            <Badge tone="success">Current plan</Badge>
                          ) : plan.featured ? (
                            <Badge tone="success">Most popular</Badge>
                          ) : null}
                        </InlineStack>

                        <div className="dc-price">
                          <strong>{plan.price}</strong>
                          <Text as="span" variant="bodyMd" tone="subdued">
                            {plan.cadence}
                          </Text>
                        </div>

                        <Text as="p" variant="bodyMd" className="dc-plan-caption">
                          {plan.caption}
                        </Text>

                        <div className="dc-divider" />

                        <ul className="dc-plan-feature-list">
                          {plan.features.map((feature) => (
                            <li key={feature}>
                              <Text as="p" variant="bodyMd">
                                {feature}
                              </Text>
                            </li>
                          ))}
                        </ul>

                        <Button
                          variant={isCurrent || plan.featured ? "primary" : "secondary"}
                          loading={busyPlan === plan.key}
                          onClick={() => handleChoosePlan(plan.key)}
                        >
                          {isCurrent ? "Re-activate" : `Use ${plan.name}`}
                        </Button>
                      </BlockStack>
                    </div>
                  </Card>
                );
              })}
            </div>

            <Card>
              <div className="dc-support-card">
                <BlockStack gap="200">
                  <Text as="h3" variant="headingLg">
                    Pricing runtime
                  </Text>
                  <Text as="p" variant="bodyMd" tone="subdued">
                    Billing status: {billing?.status || "unknown"} · Credits remaining:{" "}
                    {formatCredits(billing?.credits)}
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

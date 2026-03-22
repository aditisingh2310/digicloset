import { Page, Layout, Card, Text } from "@shopify/polaris";
import EmptyDashboard from "../components/EmptyState";
import ErrorBanner from "../components/ErrorBanner";
import Loading from "../components/Loading";
import useFirstInstall from "../hooks/useFirstInstall";
import { useState, useEffect } from "react";

export default function Home() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const hasProducts = false;

  useFirstInstall(hasProducts);

  useEffect(() => {
    setTimeout(() => setLoading(false), 800);
  }, []);

  if (loading) return <Loading />;

  return (
    <Page title="Dashboard">
      {error && <ErrorBanner message={error} />}

      <Layout>
        <Layout.Section>
          {!hasProducts ? (
            <EmptyDashboard />
          ) : (
            <Card sectioned>
              <Text variant="headingMd">Your AI Try-On Dashboard</Text>
              <p>Track performance and manage recommendations.</p>
            </Card>
          )}
        </Layout.Section>
      </Layout>
    </Page>
  );
}

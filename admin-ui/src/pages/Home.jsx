import { Page } from "@shopify/polaris";
import EmptyDashboard from "../components/EmptyState";
import useFirstInstall from "../hooks/useFirstInstall";

export default function Home() {
  // Replace with real data later
  const hasProducts = false;

  // Redirect to onboarding if needed
  useFirstInstall(hasProducts);

  return (
    <Page title="Dashboard">
      {!hasProducts ? (
        <EmptyDashboard />
      ) : (
        <div>
          <h2>Your AI Try-On Dashboard</h2>
        </div>
      )}
    </Page>
  );
}

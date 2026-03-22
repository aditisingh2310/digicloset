import { Banner } from "@shopify/polaris";

export default function ErrorBanner({ message }) {
  return (
    <Banner status="critical" title="Something went wrong">
      <p>{message || "Something went wrong. Please try again."}</p>
    </Banner>
  );
}

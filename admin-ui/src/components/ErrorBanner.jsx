import { Banner } from "@shopify/polaris";

export default function ErrorBanner({ message }) {
  return (
    <Banner status="critical">
      <p>{message || "Something went wrong."}</p>
    </Banner>
  );
}

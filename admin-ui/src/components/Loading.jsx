import { Spinner } from "@shopify/polaris";

export default function Loading() {
  return (
    <div style={{ textAlign: "center", padding: 40 }}>
      <Spinner size="large" />
      <p>Processing...</p>
    </div>
  );
}

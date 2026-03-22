import { EmptyState, Card } from "@shopify/polaris";

export default function EmptyDashboard() {
  return (
    <Card sectioned>
      <EmptyState
        heading="No products yet"
        action={{
          content: "Add products",
          onAction: () => {},
        }}
        image="https://cdn.shopify.com/s/files/1/0262/4071/2726/files/emptystate-files.png"
      >
        <p>Start by adding products to enable AI try-on.</p>
      </EmptyState>
    </Card>
  );
}

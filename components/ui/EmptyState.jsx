import { EmptyState, Card } from '@shopify/polaris';

export default function EmptyStateComponent() {
  return (
    <Card sectioned>
      <EmptyState
        heading="No data available"
        action={{ content: 'Refresh', onAction: () => window.location.reload() }}
        image="https://cdn.shopify.com/s/files/1/0262/4071/2726/files/emptystate-files.png"
      >
        <p>Start by adding or syncing data.</p>
      </EmptyState>
    </Card>
  );
}

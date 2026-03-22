import { Page, Card, Button, Text } from "@shopify/polaris";

export default function Pricing() {
  return (
    <Page title="Pricing">
      <Card sectioned>
        <Text variant="headingMd">Starter Plan</Text>
        <p>7-day free trial</p>
        <p>Then $9/month</p>
        <Button primary>Start Free Trial</Button>
      </Card>
    </Page>
  );
}

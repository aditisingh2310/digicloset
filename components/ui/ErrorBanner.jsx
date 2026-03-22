import { Banner } from '@shopify/polaris';

export default function ErrorBanner({ message }) {
  return (
    <Banner status="critical" title="Something went wrong">
      <p>{message}</p>
    </Banner>
  );
}

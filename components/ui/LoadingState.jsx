import { SkeletonPage, Layout, SkeletonBodyText } from '@shopify/polaris';

export default function LoadingState() {
  return (
    <SkeletonPage primaryAction>
      <Layout>
        <Layout.Section>
          <SkeletonBodyText lines={5} />
        </Layout.Section>
      </Layout>
    </SkeletonPage>
  );
}

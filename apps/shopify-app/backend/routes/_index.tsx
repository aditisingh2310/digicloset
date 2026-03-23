import {
  Banner,
  BlockStack,
  Button,
  Card,
  InlineStack,
  Page,
  Text,
  Spinner,
  Badge,
} from "@shopify/polaris";
import { useFetcher } from "@remix-run/react";

type Outfit = {
  id: string;
  title: string;
  description: string;
  approved?: boolean;
};

type AnalyzerResponse = {
  outfits?: Outfit[];
  error?: string;
};

export default function Index() {
  const fetcher = useFetcher();
  const isLoading = fetcher.state !== "idle";
  const data = (fetcher.data ?? null) as AnalyzerResponse | null;

  const runAI = () => {
    fetcher.submit(
      {
        productId: "gid://shopify/Product/123456789",
        imageUrl: "https://via.placeholder.com/300",
      },
      { method: "post", action: "/api/v1/analyze" }
    );
  };
  const sendFeedback = (outfitId: string, approved: boolean) => {
    fetcher.submit(
      {
        outfit_id: outfitId,
        approved,
      },
      { method: "post", action: "/api/v1/feedback" }
    );
  };

  return (
    <Page
      title="AI Analyzer"
      subtitle="Run a demo analysis, review generated outfits, and keep the approval loop tight before publishing recommendations."
    >
      <BlockStack gap="500">
        <Card>
          <BlockStack gap="300">
            <Text as="h2" variant="headingMd">
              How DigiCloset AI works
            </Text>
            <Text as="p" tone="subdued">
              DigiCloset analyzes your product imagery and metadata to create outfit suggestions that feel cohesive, on-brand, and quick to review.
            </Text>
            <InlineStack gap="300" align="space-between" blockAlign="center">
              <Text as="p" tone="subdued">
                Best results come from clean product photos and a short daily review loop on the first generated looks.
              </Text>
              <Button onClick={runAI} variant="primary" loading={isLoading}>
                Analyze Demo Product
              </Button>
            </InlineStack>
          </BlockStack>
        </Card>

        {data?.error && (
          <Banner status="critical" title="Analysis failed">
            <p>{data.error}</p>
          </Banner>
        )}

        {isLoading && (
          <Card>
            <InlineStack align="center" gap="200">
              <Spinner size="small" />
              <Text as="p">Analyzing product with AI…</Text>
            </InlineStack>
          </Card>
        )}

        {!isLoading && !data?.outfits?.length && !data?.error && (
          <Card>
            <BlockStack gap="200">
              <Text as="h2" variant="headingSm">
                No AI results yet
              </Text>
              <Text as="p" tone="subdued">
                Run the analyzer to generate AI-powered outfit suggestions for the sample product.
              </Text>
            </BlockStack>
          </Card>
        )}

        {data?.outfits?.length ? (
          <BlockStack gap="400">
            {data.outfits.map((outfit) => (
              <Card key={outfit.id}>
                <BlockStack gap="200">
                  <InlineStack align="space-between">
                    <Text as="h3" variant="headingSm">
                      {outfit.title}
                    </Text>

                    {outfit.approved && (
                      <Badge tone="success">Approved</Badge>
                    )}
                  </InlineStack>

                  <Text as="p">{outfit.description}</Text>

                  <InlineStack gap="200">
                    <Button
                      onClick={() => sendFeedback(outfit.id, true)}
                      variant="primary"
                    >
                      Approve
                    </Button>

                    <Button
                      onClick={() => sendFeedback(outfit.id, false)}
                      tone="critical"
                    >
                      Reject
                    </Button>
                  </InlineStack>
                </BlockStack>
              </Card>
            ))}
          </BlockStack>
        ) : null}
      </BlockStack>
    </Page>
  );
}

import { useState } from "react";
import { Page, Card, Button, ProgressBar, Text } from "@shopify/polaris";

export default function Onboarding() {
  const [step, setStep] = useState(1);

  const steps = [
    "Connect Store",
    "Add First Product",
    "Generate Try-On",
  ];

  const next = () => setStep((s) => Math.min(s + 1, steps.length));

  return (
    <Page title="Get Started (60 seconds)">
      <Card sectioned>
        <Text variant="headingMd">
          Step {step}: {steps[step - 1]}
        </Text>

        <div style={{ marginTop: 20 }}>
          {step === 1 && (
            <Button primary onClick={next}>
              Connect Store
            </Button>
          )}

          {step === 2 && (
            <Button primary onClick={next}>
              Upload Product
            </Button>
          )}

          {step === 3 && (
            <Button primary>
              Generate Try-On
            </Button>
          )}
        </div>

        <div style={{ marginTop: 20 }}>
          <ProgressBar progress={(step / steps.length) * 100} />
        </div>
      </Card>
    </Page>
  );
}

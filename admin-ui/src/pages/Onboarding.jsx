import { Page, Card, Button, TextContainer } from "@shopify/polaris";
import { useNavigate } from "react-router-dom";

export default function Onboarding() {
  const navigate = useNavigate();

  return (
    <Page title="Welcome">
      <Card sectioned>
        <TextContainer>
          <h2>Boost your store with AI Try-On</h2>
          <p>
            Let customers visualize outfits instantly and increase conversions.
          </p>
        </TextContainer>

        <div style={{ marginTop: 20 }}>
          <Button primary onClick={() => navigate("/")}>
            Get Started
          </Button>
        </div>
      </Card>
    </Page>
  );
}

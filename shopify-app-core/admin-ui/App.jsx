// admin-ui/App.jsx
// React + Polaris + App Bridge admin UI
import React, { useState, useEffect } from 'react';
import { AppProvider, Frame, Navigation, Page, Card, Button, Text, Toast } from '@shopify/polaris';
import { AppBridgeProvider, useAppBridge } from '@shopify/app-bridge-react';
import { Redirect } from '@shopify/app-bridge/actions';

export default function App() {
  const [billingStatus, setBillingStatus] = useState(null);
  const [toast, setToast] = useState(null);

  const app = useAppBridge();

  useEffect(() => {
    // Fetch billing status
    fetch('/api/billing/status')
      .then(res => res.json())
      .then(setBillingStatus)
      .catch(err => console.error(err));
  }, []);

  const handleSubscribe = (plan) => {
    fetch(`/api/billing/subscribe?plan=${plan}`)
      .then(res => res.json())
      .then(data => {
        if (data.confirmation_url) {
          // Redirect to Shopify for approval
          const redirect = Redirect.create(app);
          redirect.dispatch(Redirect.Action.REMOTE, data.confirmation_url);
        }
      })
      .catch(err => {
        setToast({ content: 'Subscription failed', error: true });
      });
  };

  const showToast = toast ? (
    <Toast
      content={toast.content}
      error={toast.error}
      onDismiss={() => setToast(null)}
    />
  ) : null;

  return (
    <AppProvider i18n={{}}>
      <Frame
        navigation={
          <Navigation location="/">
            <Navigation.Section
              items={[
                {
                  label: 'Dashboard',
                  icon: 'HomeMajor',
                  url: '/',
                },
                {
                  label: 'Billing',
                  icon: 'BillingStatementDollarMajor',
                  url: '/billing',
                },
              ]}
            />
          </Navigation>
        }
      >
        <Page title="DigiCloset Admin">
          <Card title="Billing Status" sectioned>
            {billingStatus ? (
              <div>
                <Text>Plan: {billingStatus.plan || 'Free'}</Text>
                <Text>Credits: {billingStatus.credits}</Text>
                <Text>Status: {billingStatus.status}</Text>
                {billingStatus.status !== 'active' && (
                  <div>
                    <Button onClick={() => handleSubscribe('starter')}>Subscribe Starter ($19)</Button>
                    <Button onClick={() => handleSubscribe('growth')}>Subscribe Growth ($49)</Button>
                    <Button onClick={() => handleSubscribe('scale')}>Subscribe Scale ($99)</Button>
                  </div>
                )}
              </div>
            ) : (
              <Text>Loading...</Text>
            )}
          </Card>
        </Page>
        {showToast}
      </Frame>
    </AppProvider>
  );
}

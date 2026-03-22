import { Navigation } from '@shopify/polaris';
import { HomeMajor } from '@shopify/polaris-icons';

export default function AppNavigation() {
  return (
    <Navigation location="/">
      <Navigation.Section
        items={[
          { label: 'Dashboard', icon: HomeMajor, url: '/' },
        ]}
      />
    </Navigation>
  );
}

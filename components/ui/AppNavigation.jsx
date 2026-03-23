import { Navigation } from "@shopify/polaris";
import { useLocation, useNavigate } from "react-router-dom";

const NAV_ITEMS = [
  { label: "Overview", path: "/" },
  { label: "Onboarding", path: "/onboarding" },
  { label: "Pricing", path: "/pricing" },
];

export default function AppNavigation() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Navigation location={location.pathname}>
      <Navigation.Section
        items={NAV_ITEMS.map((item) => ({
          label: item.label,
          url: item.path,
          selected:
            item.path === "/"
              ? location.pathname === item.path
              : location.pathname.startsWith(item.path),
          onClick: () => navigate(item.path),
        }))}
      />
      <Navigation.Section
        items={[
          {
            label: "Support",
            url: "mailto:support@digicloset.ai",
            external: true,
          },
        ]}
      />
    </Navigation>
  );
}

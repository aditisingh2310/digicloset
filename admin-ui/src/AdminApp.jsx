import { AppProvider, Frame } from "@shopify/polaris";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import AppNavigation from "../../components/ui/AppNavigation";
import Home from "./pages/Home";
import Onboarding from "./pages/Onboarding";
import Pricing from "./pages/Pricing";
import "./admin-ui.css";

const routerFuture = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
};

export default function AdminApp() {
  return (
    <AppProvider i18n={{}}>
      <Router future={routerFuture}>
        <div className="dc-admin-shell">
          <Frame navigation={<AppNavigation />}>
            <div className="dc-admin-frame">
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/onboarding" element={<Onboarding />} />
                <Route path="/pricing" element={<Pricing />} />
              </Routes>
            </div>
          </Frame>
        </div>
      </Router>
    </AppProvider>
  );
}

import { act, render, screen } from "@testing-library/react";
import { AppProvider, Frame } from "@shopify/polaris";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AppNavigation from "../../../components/ui/AppNavigation";
import Home from "../pages/Home";
import Onboarding from "../pages/Onboarding";
import Pricing from "../pages/Pricing";

const routerFuture = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
};

function renderWithProviders(node, route = "/") {
  window.history.pushState({}, "Test", route);
  return render(
    <AppProvider i18n={{}}>
      <MemoryRouter initialEntries={[route]} future={routerFuture}>
        <Frame>{node}</Frame>
      </MemoryRouter>
    </AppProvider>,
  );
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input) => {
      const url = String(input);

      if (url.includes("/api/merchant/dashboard")) {
        return new Response(
          JSON.stringify({
            shop: "local-dev.myshopify.com",
            tryons_generated: 2,
            credits_used: 2,
            generation_history: [
              { id: "job-1", product_id: "demo-1", status: "completed", created_at: "2026-03-26T00:00:00" },
            ],
            widget_enabled: true,
          }),
          { status: 200 },
        );
      }

      if (url.includes("/api/billing/status")) {
        return new Response(
          JSON.stringify({
            plan: "starter",
            status: "active",
            credits: 198,
            reset_date: null,
          }),
          { status: 200 },
        );
      }

      if (url.includes("/api/onboarding/status")) {
        return new Response(
          JSON.stringify({
            trial_days_remaining: 7,
            usage_remaining: 198,
            subscription_active: true,
            onboarding_complete: true,
          }),
          { status: 200 },
        );
      }

      if (url.includes("/api/merchant/settings")) {
        return new Response(
          JSON.stringify({
            widget_enabled: true,
            updated_at: "2026-03-26T00:00:00",
          }),
          { status: 200 },
        );
      }

      if (url.includes("/api/billing/subscribe") || url.includes("/api/billing/activate")) {
        return new Response(JSON.stringify({ subscription_id: "local-starter" }), { status: 200 });
      }

      return new Response(JSON.stringify({ detail: "not found" }), { status: 404 });
    }),
  );
});

describe("Admin UI smoke coverage", () => {
  it("renders navigation items for the active admin shell", () => {
    renderWithProviders(<AppNavigation />, "/");

    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Onboarding")).toBeInTheDocument();
    expect(screen.getByText("Pricing")).toBeInTheDocument();
    expect(screen.getByText("Support")).toBeInTheDocument();
  });

  it("renders the overview page after the loading skeleton", async () => {
    vi.useFakeTimers();
    renderWithProviders(<Home />, "/");

    await act(async () => {
      vi.runAllTimers();
    });

    expect(screen.getAllByText("DigiCloset command center").length).toBeGreaterThan(0);
    expect(screen.getByText("Go-live checklist")).toBeInTheDocument();
  });

  it("renders the onboarding page", () => {
    renderWithProviders(<Onboarding />, "/onboarding");

    expect(screen.getAllByText("Launch onboarding").length).toBeGreaterThan(0);
    expect(screen.getByText("Recommended launch sequence")).toBeInTheDocument();
  });

  it("renders the pricing page", () => {
    renderWithProviders(<Pricing />, "/pricing");

    expect(screen.getByText("Transparent pricing")).toBeInTheDocument();
    expect(screen.getByText("Most popular")).toBeInTheDocument();
  });
});

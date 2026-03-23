import { act, render, screen } from "@testing-library/react";
import { AppProvider, Frame } from "@shopify/polaris";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import AppNavigation from "../../../components/ui/AppNavigation";
import Home from "../pages/Home";
import Onboarding from "../pages/Onboarding";
import Pricing from "../pages/Pricing";

function renderWithProviders(node, route = "/") {
  window.history.pushState({}, "Test", route);
  return render(
    <AppProvider i18n={{}}>
      <MemoryRouter initialEntries={[route]}>
        <Frame>{node}</Frame>
      </MemoryRouter>
    </AppProvider>,
  );
}

afterEach(() => {
  vi.useRealTimers();
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

    expect(screen.getByText("DigiCloset command center")).toBeInTheDocument();
    expect(screen.getByText("Go-live checklist")).toBeInTheDocument();
  });

  it("renders the onboarding page", () => {
    renderWithProviders(<Onboarding />, "/onboarding");

    expect(screen.getByText("Launch onboarding")).toBeInTheDocument();
    expect(screen.getByText("Recommended launch sequence")).toBeInTheDocument();
  });

  it("renders the pricing page", () => {
    renderWithProviders(<Pricing />, "/pricing");

    expect(screen.getByText("Transparent pricing")).toBeInTheDocument();
    expect(screen.getByText("Most popular")).toBeInTheDocument();
  });
});

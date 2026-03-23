import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function useFirstInstall(hasProducts) {
  const navigate = useNavigate();

  useEffect(() => {
    if (!hasProducts) {
      navigate("/onboarding");
    }
  }, [hasProducts, navigate]);
}

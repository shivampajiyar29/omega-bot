"use client";

import { useEffect } from "react";
import TradingPage from "@/app/trading/page";
import { useStore } from "@/store/useStore";

export default function PaperTradingRoute() {
  const { setTradingMode } = useStore();

  useEffect(() => {
    setTradingMode("paper");
  }, [setTradingMode]);

  return <TradingPage />;
}

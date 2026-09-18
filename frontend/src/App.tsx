/**
 * SkyGuard AI — Meteorological Quality Control & Sensor Anomaly Platform
 * Operations Navigation & TanStack Query Root Setup
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './layouts/AppLayout';
import { NetworkOverview } from './pages/NetworkOverview';
import { LiveMonitoring } from './pages/LiveMonitoring';
import { StationDetails } from './pages/StationDetails';
import { StationsCatalog } from './pages/StationsCatalog';
import { AnomalyInvestigation } from './pages/AnomalyInvestigation';
import { AnomalyRegistry } from './pages/AnomalyRegistry';
import { SensorHealth } from './pages/SensorHealth';
import { CorrectionReview } from './pages/CorrectionReview';
import { HistoricalAnalysis } from './pages/HistoricalAnalysis';
import { SystemObservability } from './pages/SystemObservability';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 10000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/network" replace />} />
            <Route path="/network" element={<NetworkOverview />} />
            <Route path="/live" element={<LiveMonitoring />} />
            <Route path="/stations" element={<StationsCatalog />} />
            <Route path="/stations/:stationId" element={<StationDetails />} />
            <Route path="/anomalies" element={<AnomalyRegistry />} />
            <Route path="/anomalies/:eventId" element={<AnomalyInvestigation />} />
            <Route path="/health" element={<SensorHealth />} />
            <Route path="/corrections" element={<CorrectionReview />} />
            <Route path="/history" element={<HistoricalAnalysis />} />
            <Route path="/system" element={<SystemObservability />} />
            <Route path="*" element={<Navigate to="/network" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

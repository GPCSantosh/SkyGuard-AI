import React from 'react';
import { Outlet } from 'react-router-dom';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { useRealtimeStream } from '../hooks/useRealtimeStream';
import { DegradedModeBanner } from '../components/StateFeedback';

export const AppLayout: React.FC = () => {
  const { isDegraded } = useRealtimeStream();

  return (
    <div className="h-screen w-screen flex flex-col bg-canvas text-slate-100 overflow-hidden">
      {/* 40px Top Operations Bar */}
      <TopBar />

      {/* Optional Degraded Mode Alert Banner */}
      {isDegraded && <DegradedModeBanner />}

      {/* Main App Workspace: Sidebar + Scrollable View Canvas */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-4 bg-canvas">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

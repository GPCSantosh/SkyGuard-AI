<<<<<<< HEAD
/**
 * SkyGuard AI — Master Application Layout
 * Top Command Bar navigation model without permanent sidebars.
 * Centers fluid analytical workspaces, scientific toolbars, and responsive panels.
 */

import React from 'react';
import { Outlet } from 'react-router-dom';
import { TopCommandBar } from './TopCommandBar';

export const AppLayout: React.FC = () => {
=======
import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { ActiveSourceBanner } from '../components/common/ActiveSourceBanner';
import { CsvPreviewModal } from '../components/common/CsvPreviewModal';
import { DataSourceSelectorModal } from '../components/common/DataSourceSelectorModal';
import { DatasetInfoDrawer } from '../components/common/DatasetInfoDrawer';
import { RunHistoryModal } from '../components/common/RunHistoryModal';
import { DegradedModeBanner } from '../components/StateFeedback';
import { useRealtimeStream } from '../hooks/useRealtimeStream';
import { useRunContext } from '../hooks/useRunContext';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export const AppLayout: React.FC = () => {
  const { isDegraded } = useRealtimeStream();
  const { context, selectSource } = useRunContext();

  const [isSelectorOpen, setIsSelectorOpen] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isCsvModalOpen, setIsCsvModalOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

>>>>>>> 6f03007298457cd197e1278299945efcd0c78dbb
  return (
    <div className="flex flex-col min-h-screen w-screen bg-[#070B12] text-[#F8FAFC]">
      {/* Top Command Bar */}
      <TopCommandBar />

<<<<<<< HEAD
      {/* Main Full-Width Analytical Workspace */}
      <main className="flex-1 w-full max-w-[1920px] mx-auto p-3 sm:p-4 md:p-5 overflow-x-hidden">
        <Outlet />
      </main>
=======
      {/* Active Source & Run Context Banner */}
      <ActiveSourceBanner
        context={context}
        onOpenSelector={() => setIsSelectorOpen(true)}
        onOpenDrawer={() => setIsDrawerOpen(true)}
        onOpenHistory={() => setIsHistoryOpen(true)}
      />

      {/* Optional Degraded Mode Alert Banner */}
      {isDegraded && <DegradedModeBanner />}

      {/* Main App Workspace: Sidebar + Scrollable View Canvas */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-4 bg-canvas">
          <Outlet />
        </main>
      </div>

      {/* Modals & Drawers */}
      <DataSourceSelectorModal
        isOpen={isSelectorOpen}
        onClose={() => setIsSelectorOpen(false)}
        onSelect={selectSource}
        onOpenCsvModal={() => setIsCsvModalOpen(true)}
      />

      <DatasetInfoDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        context={context}
      />

      <CsvPreviewModal
        isOpen={isCsvModalOpen}
        onClose={() => setIsCsvModalOpen(false)}
        onConfirm={selectSource}
      />

      <RunHistoryModal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
      />
>>>>>>> 6f03007298457cd197e1278299945efcd0c78dbb
    </div>
  );
};

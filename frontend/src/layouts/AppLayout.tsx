/**
 * SkyGuard AI — Master Application Layout
 * Top Command Bar navigation model without permanent sidebars.
 * Centers fluid analytical workspaces, scientific toolbars, and responsive panels.
 */

import React from 'react';
import { Outlet } from 'react-router-dom';
import { TopCommandBar } from './TopCommandBar';

export const AppLayout: React.FC = () => {
  return (
    <div className="flex flex-col min-h-screen w-screen bg-[#070B12] text-[#F8FAFC]">
      {/* Top Command Bar */}
      <TopCommandBar />

      {/* Main Full-Width Analytical Workspace */}
      <main className="flex-1 w-full max-w-[1920px] mx-auto p-3 sm:p-4 md:p-5 overflow-x-hidden">
        <Outlet />
      </main>
    </div>
  );
};

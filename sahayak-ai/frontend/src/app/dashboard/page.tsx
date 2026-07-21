"use client";

import { Topbar } from "@/components/layout/topbar";
import { DailyBrief } from "@/components/dashboard/daily-brief";
import { MetricCards } from "@/components/dashboard/metric-cards";
import { OnboardingHero } from "@/components/dashboard/onboarding-hero";
import { PriorityCases } from "@/components/dashboard/priority-cases";
import { TaskList } from "@/components/dashboard/task-list";
import { useBrief, useHealth } from "@/lib/hooks";

export default function DashboardPage() {
  const { data: brief, isLoading, isError } = useBrief();
  const { data: health } = useHealth();

  const total = brief?.metrics.total_beneficiaries;
  const showOnboarding =
    health?.active_mode === "LIVE" && total === 0 && !isLoading && !isError;

  return (
    <>
      <Topbar
        title="Dashboard"
        subtitle="Your field team's command center for the day"
      />
      <main className="flex-1 overflow-y-auto p-4 sm:p-6">
        {showOnboarding ? (
          <div className="space-y-6">
            <OnboardingHero />
            <MetricCards
              metrics={brief?.metrics}
              isLoading={isLoading}
              isError={isError}
            />
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-3">
            {/* Left column — brief + metrics */}
            <div className="space-y-6 md:col-span-2">
              <MetricCards
                metrics={brief?.metrics}
                isLoading={isLoading}
                isError={isError}
              />
              <DailyBrief />
            </div>

            {/* Right column — checklist + urgent cases */}
            <div className="space-y-6">
              <PriorityCases />
              <TaskList />
            </div>
          </div>
        )}
      </main>
    </>
  );
}

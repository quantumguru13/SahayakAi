"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { Topbar } from "@/components/layout/topbar";
import { ProfileCard } from "@/components/beneficiary/profile-card";
import { Timeline } from "@/components/beneficiary/timeline";
import { UrgencyPanel } from "@/components/beneficiary/urgency-panel";
import { WelfareRecommender } from "@/components/schemes/welfare-recommender";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useBeneficiary } from "@/lib/hooks";

export default function BeneficiaryDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const { data: b, isLoading, isError } = useBeneficiary(id);

  return (
    <>
      <Topbar title="Case File" subtitle="Beneficiary profile & recommendations" />
      <main className="flex-1 overflow-y-auto p-6">
        <Link
          href="/beneficiaries"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to beneficiaries
        </Link>

        {isError ? (
          <Card>
            <CardContent className="py-12 text-center text-sm text-muted-foreground">
              Beneficiary not found.
            </CardContent>
          </Card>
        ) : isLoading || !b ? (
          <div className="grid gap-6 md:grid-cols-3">
            <Skeleton className="h-96 md:col-span-1" />
            <Skeleton className="h-96 md:col-span-2" />
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-3">
            <div className="space-y-6 md:col-span-1">
              <ProfileCard beneficiary={b} />
              {b.urgency && <UrgencyPanel urgency={b.urgency} />}
            </div>
            <div className="space-y-6 md:col-span-2">
              <WelfareRecommender beneficiaryId={b.id} />
              <Timeline beneficiaryId={b.id} />
            </div>
          </div>
        )}
      </main>
    </>
  );
}

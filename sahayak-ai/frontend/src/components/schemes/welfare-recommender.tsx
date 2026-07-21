"use client";

import { Landmark } from "lucide-react";

import { SchemeMatchList } from "./scheme-match-list";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSchemes } from "@/lib/hooks";

export function WelfareRecommender({
  beneficiaryId,
  compact,
}: {
  beneficiaryId: string;
  compact?: boolean;
}) {
  const { data, isLoading, isError, refetch } = useSchemes(beneficiaryId);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Landmark className="h-4 w-4 text-primary" />
          Matched Welfare Schemes
        </CardTitle>
      </CardHeader>
      <CardContent>
        <SchemeMatchList
          matches={data}
          beneficiaryId={beneficiaryId}
          isLoading={isLoading}
          isError={isError}
          onRetry={() => refetch()}
          compact={compact}
        />
      </CardContent>
    </Card>
  );
}

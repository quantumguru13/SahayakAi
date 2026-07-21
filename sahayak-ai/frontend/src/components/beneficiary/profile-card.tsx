"use client";

import {
  BadgeIndianRupee,
  Fingerprint,
  MapPin,
  Stethoscope,
  User,
} from "lucide-react";

import { PriorityBadge } from "@/components/shared/priority-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { formatINR } from "@/lib/utils";
import type { Beneficiary } from "@/lib/types";

export function ProfileCard({ beneficiary }: { beneficiary: Beneficiary }) {
  const b = beneficiary;
  return (
    <Card className="shadow-sm">
      <CardHeader className="flex-row items-center gap-3.5 space-y-0 pb-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary/15 text-lg font-bold text-primary ring-2 ring-primary/20">
          {b.name.charAt(0)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h2 className="truncate text-base font-bold text-foreground">{b.name}</h2>
            <PriorityBadge priority={b.current_priority} />
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground font-medium">
            {[b.age ? `${b.age} years` : null, b.gender].filter(Boolean).join(" · ") ||
              "Profile details pending"}
          </p>
        </div>
      </CardHeader>
      <CardContent className="space-y-3.5 pt-1">
        <Row
          icon={<Fingerprint className="h-4 w-4" />}
          label="Government ID"
          value={
            b.government_id_type
              ? `${b.government_id_type} · ${b.government_id_number_masked ?? "••••"}`
              : "Not captured"
          }
        />
        <Row
          icon={<BadgeIndianRupee className="h-4 w-4" />}
          label="Annual Household Income"
          value={formatINR(b.annual_income)}
        />
        <Row
          icon={<MapPin className="h-4 w-4" />}
          label="Location"
          value={b.state_location ?? "—"}
        />
        <Row
          icon={<User className="h-4 w-4" />}
          label="Disability Status"
          value={b.is_disabled ? "Registered (PwD)" : "None recorded"}
        />
        <div className="flex items-start gap-3">
          <span className="mt-0.5 text-muted-foreground shrink-0">
            <Stethoscope className="h-4 w-4" />
          </span>
          <div className="flex-1">
            <div className="text-xs font-medium text-muted-foreground">
              Detected Medical Conditions
            </div>
            {b.medical_conditions.length === 0 ? (
              <div className="text-sm font-medium text-foreground mt-0.5">None detected</div>
            ) : (
              <div className="mt-1.5 flex flex-wrap gap-1">
                {b.medical_conditions.map((c) => (
                  <Badge key={c} variant="destructive" className="text-[10px] px-2 py-0.5">
                    {c}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function Row({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 text-muted-foreground shrink-0">{icon}</span>
      <div>
        <div className="text-xs font-medium text-muted-foreground">{label}</div>
        <div className="text-sm font-medium text-foreground mt-0.5">{value}</div>
      </div>
    </div>
  );
}

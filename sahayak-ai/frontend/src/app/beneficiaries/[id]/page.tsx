import { BeneficiaryDetail } from "./beneficiary-detail";
import { PLACEHOLDER_ID } from "./placeholder-id";

/**
 * `output: "export"` has to know every dynamic path at build time, but case ids
 * are created at runtime. So we prerender one placeholder page and let Firebase
 * Hosting rewrite /beneficiaries/<anything> onto it — the component then reads
 * the real id off the URL. See the rewrite in firebase.json.
 */
export function generateStaticParams() {
  return [{ id: PLACEHOLDER_ID }];
}

export default function BeneficiaryDetailPage() {
  return <BeneficiaryDetail />;
}

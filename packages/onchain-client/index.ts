// packages/onchain-client/index.ts - TS client for apps/onchain.
// Use from dashboard or any Node service.

const BASE = process.env.ONCHAIN_SERVICE_URL ?? "http://localhost:8001";

export const CLAIM_TAP = 1;
export const CLAIM_VOICE = 2;
export const CLAIM_CASEFILE = 3;
export const CLAIM_SIGNAL_CARD = 4;

export interface CommitResponse {
  tx_hash: string;
  explorer_url: string | null;
  block_number: number | null;
  claim_type: number;
  claim_type_label: string;
  committed_at: string;
  mocked: boolean;
}

export async function commit(
  claimType: number,
  claimHashHex: string,
): Promise<CommitResponse> {
  const r = await fetch(`${BASE}/commit`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ claim_type: claimType, claim_hash: claimHashHex }),
  });
  if (!r.ok) throw new Error(`commit failed: ${r.status} ${await r.text()}`);
  return r.json();
}

export async function sign(contentB64: string): Promise<{
  signature_b64: string;
  pubkey_b64: string;
  algo: string;
}> {
  const r = await fetch(`${BASE}/sign`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ content_b64: contentB64 }),
  });
  if (!r.ok) throw new Error(`sign failed: ${r.status} ${await r.text()}`);
  return r.json();
}

export async function verifyKey(): Promise<{ pubkey_b64: string; algo: string }> {
  const r = await fetch(`${BASE}/verify-key`);
  if (!r.ok) throw new Error(`verify-key failed: ${r.status}`);
  return r.json();
}

export interface GetCommitResponse {
  tx_hash: string;
  claim_type: number | null;
  claim_type_label: string | null;
  claim_hash: string | null;
  signer_role: string | null;
  signer_address: string | null;
  block_number: number | null;
  block_timestamp: number | null;
  verified: boolean;
  status: number | null;
  source: string;
  explorer_url?: string | null;
  note?: string;
}

export async function getCommit(txHash: string): Promise<GetCommitResponse> {
  const r = await fetch(`${BASE}/commit/${txHash}`);
  if (!r.ok) throw new Error(`getCommit failed: ${r.status} ${await r.text()}`);
  return r.json();
}

export interface VerifyResponse {
  claim_hash: string;
  claim_type: number | null;
  count: number;
  matches: Array<Record<string, unknown>>;
  source: string;
}

export async function verifyClaim(
  claimHashHex: string,
  claimType?: number,
): Promise<VerifyResponse> {
  const url = new URL(`${BASE}/verify`);
  url.searchParams.set("claim_hash", claimHashHex);
  if (claimType !== undefined) url.searchParams.set("claim_type", String(claimType));
  const r = await fetch(url);
  if (!r.ok) throw new Error(`verifyClaim failed: ${r.status} ${await r.text()}`);
  return r.json();
}

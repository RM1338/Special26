// Exact copy from docs/09-user-flow.md. No em dashes.
export const PROBES: Record<string, { label: string; engines: string[] }> = {
  P01_ENTITY: { label: "Finding {org}'s official website", engines: ["Google"] },
  P02_SENDER: { label: "Comparing the sender's domain with {org}'s", engines: [] },
  P03_HEADERS: { label: "Reading the email's authentication", engines: [] },
  P04_FRAUD_NOTICE: { label: "Looking for {org}'s own fraud warnings", engines: ["Google"] },
  P05_CHATTER: { label: "Searching news and forums for complaints", engines: ["Google", "News", "Forums"] },
  P06_IDENTIFIER_TRACE: { label: "Checking if the UPI ID, phone or domain was reported", engines: ["Google"] },
  P07_ROLE: { label: "Checking Google Jobs for this role", engines: ["Jobs"] },
  P08_OFFICE: { label: "Checking the office on Google Maps", engines: ["Maps"] },
  P09_IMAGE: { label: "Checking where the HR photo appears online (Google Lens)", engines: ["Lens"] },
  P10_TEMPLATE: { label: "Checking if this letter's wording was reported", engines: ["Google"] },
  P11_POLICY: { label: "Checking the payment and process", engines: [] },
  P12_DOMAIN_AGE: { label: "Checking how old the domain is", engines: [] },
};

export const ENGINE_NAMES: Record<string, string> = {
  google: "Google Search", google_news: "Google News", google_forums: "Google Forums", google_jobs: "Google Jobs",
  google_maps: "Google Maps", google_lens: "Google Lens",
};

export const SKIP_REASONS: Record<string, string> = {
  skipped_no_input: "nothing in the offer to check",
  skipped_no_official_domain: "no official website found",
  skipped_budget: "search budget used up",
  skipped_replay_miss: "no recorded result in demo mode",
  skipped_no_public_url: "image search not available on this server",
  skipped_forwarded: "this email was forwarded. Download the original to check authentication",
  unsupported: "not supported for this domain",
};

export const TIER_ICON: Record<string, string> = { red: "⛔", amber: "⚠️", green: "✅", grey: "❔" };

export const FAMILY_NAMES: Record<string, string> = {
  identity: "Identity", process: "Payment and process", reputation: "Reports and warnings",
  artifact: "Images and wording", existence: "Office and role",
};

export const ERRORS: Record<string, string> = {
  empty: "Paste the offer text or upload a file.",
  PAYLOAD_TOO_LARGE: "That file is over 5 MB. Try a screenshot of the first page.",
  UNSUPPORTED_MEDIA: "We can read PDF, PNG, JPG and .eml files.",
  BUDGET_EXHAUSTED: "We've hit today's search limit. Try again after 5:30 AM IST, or use the demo examples.",
  EXPIRED: "This check expired. Start again, it only takes a minute.",
  OCR_UNAVAILABLE: "We couldn't read text from the image. Paste the text if you can. We'll still check the image itself.",
};
export const rateLimited = (minutes: number) =>
  `Too many checks from this connection. Try again in ${minutes} minutes.`;

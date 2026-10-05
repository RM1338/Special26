"""P09_IMAGE: is the HR photo or letter reused? Google Lens, 1 to 2 calls (08 §4, D-27, D-38)."""
import re
from pathlib import Path
from urllib.parse import urlparse

from rapidfuzz import fuzz

from special26 import seeds
from special26.claims.models import ClaimType as T
from special26.claims.regexes import has_scam_word
from special26.domains.classify import reg
from special26.errors import UpstreamError
from special26.intake.images import for_lens
from special26.probes.base import Probe, ProbeContext, ProbeResult, serp_receipt

NAME = re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b")


class NoImageRoute(Exception):
    """Neither SerpApi upload nor a public signed URL is available."""


def host(m: dict) -> str:
    return urlparse(m.get("link", "")).netloc.lower().removeprefix("www.")


def lens_receipt(q: str, key: str, m: dict):
    return serp_receipt("google_lens", q, key, {"position": m.get("position"), "title": m.get("title"),
                                                "link": m.get("link"), "snippet": m.get("source")})


class P09Image(Probe):
    id = "P09_IMAGE"
    engine = "google_lens"
    depends_on = ("P01_ENTITY",)
    max_calls = 1
    timeout_s = 35.0                              # Lens measured up to 16.6 s (D-29)

    def _images(self, ctx: ProbeContext) -> dict[str, dict]:
        out = {}
        for c in ctx.claims.all(T.image):
            out.setdefault(c.value["role"], c.value)
        return out

    def applicable(self, ctx: ProbeContext):
        return None if {"hr_photo", "offer_image"} & set(self._images(ctx)) else "skipped_no_input"

    async def _lens(self, ctx: ProbeContext, artifact_id: int, lens_type: str) -> tuple[dict, str, str]:
        a = next(x for x in ctx.repo.artifacts(ctx.check_id) if x["id"] == artifact_id)
        params = {"engine": "google_lens", "type": lens_type, "image_sha256": a["sha256"]}
        if ctx.settings.mode == "replay":
            params["image_id"] = "replay"                       # keyed by sha256 only (D-12)
        else:
            try:
                params["image_id"] = await ctx.serp.upload_image(for_lens(Path(a["storage_path"]).read_bytes()))
            except (UpstreamError, OSError, TypeError):
                if not ctx.settings.public_base_url:
                    raise NoImageRoute from None
                from special26.api.public_img import sign
                params["url"] = f"{ctx.settings.public_base_url.rstrip('/')}/public/img/" \
                                f"{sign(ctx.settings.share_salt, a['sha256'])}"
        data, key = await self.search(ctx, params)
        return data, key, f"Google Lens ({lens_type.replace('_', ' ')}) of the uploaded image"

    async def run(self, ctx: ProbeContext) -> ProbeResult:
        try:
            return await self._run(ctx)
        except NoImageRoute:
            return self.result([]).model_copy(update={"status": "skipped_no_public_url"})

    async def _run(self, ctx: ProbeContext) -> ProbeResult:
        imgs, f = self._images(ctx), []
        official = set(ctx.official)
        stock = seeds.lines("stock_photo_domains.txt")
        hr = ctx.claims.first(T.hr_person)
        hr_name = hr.value.get("name") if hr else None
        if "hr_photo" in imgs:
            claim = next(c for c in ctx.claims.all(T.image) if c.value["role"] == "hr_photo")
            data, key, q = await self._lens(ctx, imgs["hr_photo"]["artifact_id"], "exact_matches")
            matches = data.get("exact_matches", [])
            s = next((m for m in matches if any(host(m) == d or host(m).endswith("." + d) for d in stock)), None)
            if s:
                f.append(self.finding("P09_STOCK_PHOTO", lens_receipt(q, key, s), [claim.id], source=host(s)))
            others = {}
            for m in matches:
                names = NAME.findall(m.get("title", ""))
                if names and all(not hr_name or fuzz.ratio(n, hr_name) < 70 for n in names):
                    others.setdefault(reg(host(m)), m)
            if len(others) >= 3:
                first = next(iter(others.values()))
                f.append(self.finding("P09_PHOTO_OTHER_NAMES", lens_receipt(q, key, first), [claim.id],
                                      n=len(others)))
            if hr_name:
                off = next((m for m in matches if (reg(host(m)) in official or "linkedin.com/in/" in m.get("link", ""))
                            and fuzz.partial_ratio(hr_name.lower(), m.get("title", "").lower()) >= 80), None)
                if off:
                    f.append(self.finding("P09_PHOTO_OFFICIAL", lens_receipt(q, key, off), [claim.id, hr.id],
                                          source=host(off), name=hr_name))
        letter_ok = ctx.settings.credit_budget_per_check - ctx.reserved_calls >= 3      # 05 §8
        if "offer_image" in imgs and letter_ok:
            claim = next(c for c in ctx.claims.all(T.image) if c.value["role"] == "offer_image")
            data, key, q = await self._lens(ctx, imgs["offer_image"]["artifact_id"], "visual_matches")
            rep = next((m for m in data.get("visual_matches", [])
                        if has_scam_word(f"{m.get('title', '')} {m.get('source', '')}")), None)
            if rep:
                f.append(self.finding("P09_LETTER_REPORTED", lens_receipt(q, key, rep), [claim.id], source=host(rep)))
        return self.result(f)

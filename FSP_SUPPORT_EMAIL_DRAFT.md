# FSP Support Email — Draft

**Submit at:** https://support.flightschedulepro.com/hc/en-us/requests/new
**Or:** in-app help button (top right of app.flightschedulepro.com)

---

**Subject:** API access + milestone-event automation — Provectus

Hi FSP team,

Two related asks from Provectus.

**1. API access.** We're building an internal analytics tool to measure cost, duration, flight hours, and event counts per student / per rating / per training milestone, sourced from our FSP data. We've reviewed developer.flightschedulepro.com and want to use the API rather than CSV exports.

Could you confirm:

- Whether our company currently has an active API subscription, and if not, what's required to add one (cost, contract terms, lead time).
- That my account has, or can be granted, the "Can Manage Company Settings" permission needed to generate keys at Settings → API Access.
- Our FSP Company ID (OperatorId) — I'll also pull it from Settings → General → Company → Company Profile, but a confirmation helps.
- Anything we should know about the 60-call/60-second rate limit if we're backfilling ~50 students of historical data.

**2. Milestone events.** I understand FSP is working on milestone-event automation triggers. We'd like to align on the per-rating milestone list we'll be measuring against so what you build matches what we report on:

- PPL: start → first solo → cross-country solos complete → initial checkride
- IFR: start → cross-country PIC time-building complete → initial checkride
- ASEL COM, AMEL, CFI, CFII, MEI: start → initial checkride

What's the current timeline on milestone events, and is there a way for us to be on the early-access list?

**3. One quick API doc question.** The Scheduling API spec lists the base URL as `https://integration-fsp.flightschedulepro.com/scheduling/v1.0`, but the other three APIs use `https://usc-api.flightschedulepro.com/...`. Is the Scheduling URL a doc typo, or is Scheduling actually served from a different host?

Thanks,
Olsen Durkovich
Provectus
durkovich.olsen@gmail.com

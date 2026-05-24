# Alumni Survey — Form Spec (for boss review)

This is the exact copy + structure for the Google Form. Boss approves wording before the form is built. Estimated completion time for an alum: 3–5 minutes.

---

## Form title

**Provectus Aviation — Alumni Training Recap**

## Intro screen (description field at top of form)

> One section per rating. Skip any you didn't complete at Provectus. Month + year is fine — approximate dates are OK.
>
> 3–5 minutes.

---

## Section 1 — About you

**Q1. Full name** *(short answer, required)*
> Match it to how Provectus has you on file if possible — middle name or nickname is fine to include.

**Q2. Email** *(short answer, required, email validation)*
> So we can follow up if anything in your responses needs clarifying.

---

## Section 2 — Private Pilot (PPL)

**Q3. Did you complete your PPL at Provectus?** *(multiple choice, required)*
- Yes → continue with section
- No → skip to Section 3

**Q4. PPL training start** *(month + year, e.g. "March 2022")*

**Q5. First solo flight** *(month + year)*

**Q6. Cross-country solos completed** *(month + year — when you finished your PPL XC solo requirement)*

**Q7. PPL checkride pass date** *(month + year)*

---

## Section 3 — Instrument Rating (IFR)

**Q8. Did you complete your IFR at Provectus?** *(multiple choice, required)*
- Yes → continue
- No → skip to Section 4

**Q9. IFR training start** *(month + year)*

**Q10. Cross-country PIC time-building completed** *(month + year — when you finished the 50 hours XC PIC for IFR)*

**Q11. IFR checkride pass date** *(month + year)*

---

## Section 4 — Commercial Single-Engine (ASEL COM)

**Q12. Did you complete your ASEL COM at Provectus?** *(multiple choice, required)*
- Yes → continue
- No → skip

**Q13. ASEL COM training start** *(month + year)*

**Q14. ASEL COM checkride pass date** *(month + year)*

---

## Section 5 — Multi-Engine (AMEL)

**Q15. Did you complete your AMEL at Provectus?**
- Yes → continue
- No → skip

**Q16. AMEL training start** *(month + year)*

**Q17. AMEL checkride pass date** *(month + year)*

---

## Section 6 — CFI

**Q18. Did you complete your initial CFI at Provectus?**
- Yes → continue
- No → skip

**Q19. CFI training start** *(month + year)*

**Q20. CFI checkride pass date** *(month + year)*

---

## Section 7 — CFII

**Q21. Did you complete your CFII at Provectus?**
- Yes → continue
- No → skip

**Q22. CFII training start** *(month + year)*

**Q23. CFII checkride pass date** *(month + year)*

---

## Section 8 — MEI

**Q24. Did you complete your MEI at Provectus?**
- Yes → continue
- No → skip

**Q25. MEI training start** *(month + year)*

**Q26. MEI checkride pass date** *(month + year)*

---

## Section 9 — Anything else

**Q27. Anything we should know about your training timeline?** *(long answer, optional)*
> E.g. gaps for medical, transfers in from another school, paused for finals — anything that explains an unusual stretch of dates.

---

## Form behavior

- "Yes/No" gate at top of each rating section drives Google Forms' "Go to section based on answer" branching.
- All date fields: free-text "month + year" (e.g., "March 2022"). Don't use Google Forms' date picker — it requires day-precision and slows alumni down on recall.
- Email field has Google Forms' built-in email validation.
- "Submit another response" disabled at the end (one alum = one form).
- Confirmation message: *"Thanks — that's it. If anything comes back unclear we may follow up by email. — Operations, Provectus Aviation"*

---

## Implementation notes (for whoever builds the form)

- Use **sections** (not just questions) so the "skip to section based on answer" branching works.
- Section title can be the rating name (e.g., "Private Pilot (PPL)").
- Set form to **collect email addresses = off** (we ask in Q2 to keep it consistent with the form, not the Google account).
- Pre-filled link template — for a personalized send: `?entry.{Q1_id}=Olsen+Durkovich` (Google Forms gives the entry IDs after the form is built; will populate the name field).

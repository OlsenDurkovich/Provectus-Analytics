// Provectus Alumni Training Recap — form builder
// HOW TO USE:
//   1. Go to https://script.google.com → New project
//   2. Paste this whole file in
//   3. Click Run on buildAlumniForm. Grant the permissions it asks for.
//   4. Check the Execution log — it prints the live form URL.
//
// Re-running creates ANOTHER form. Delete old ones from your Drive if needed.

function buildAlumniForm() {
  const form = FormApp.create('Provectus Aviation — Alumni Training Recap');
  form.setDescription(
    'One section per rating. Skip any you didn\'t complete at Provectus. ' +
    'Approximate dates are OK — guess the day if you have to.\n\n3–5 minutes.'
  );
  form.setCollectEmail(false);
  form.setAllowResponseEdits(true);
  form.setLimitOneResponsePerUser(false);
  form.setConfirmationMessage(
    'Thanks — that\'s it. If anything comes back unclear we may follow up by email. — Operations, Provectus Aviation'
  );

  // SECTION 1 — About you
  form.addTextItem()
    .setTitle('Full name')
    .setHelpText('Match it to how Provectus has you on file if possible — middle name or nickname is fine to include.')
    .setRequired(true);

  form.addTextItem()
    .setTitle('Email')
    .setHelpText('So we can follow up if anything needs clarifying.')
    .setRequired(true)
    .setValidation(FormApp.createTextValidation().requireTextIsEmail().build());

  const ratings = [
    {
      key: 'PPL',
      title: 'Private Pilot (PPL)',
      gate: 'Did you complete your PPL at Provectus?',
      dateFields: [
        ['PPL training start', ''],
        ['First solo flight', ''],
        ['Cross-country solos completed', 'When you finished your PPL XC solo requirement'],
        ['PPL checkride pass date', '']
      ]
    },
    {
      key: 'IFR',
      title: 'Instrument Rating (IFR)',
      gate: 'Did you complete your IFR at Provectus?',
      dateFields: [
        ['IFR training start', ''],
        ['Cross-country PIC time-building completed', 'When you finished the 50 hours XC PIC for IFR'],
        ['IFR checkride pass date', '']
      ]
    },
    {
      key: 'ASEL_COM',
      title: 'Commercial Single-Engine (ASEL COM)',
      gate: 'Did you complete your ASEL COM at Provectus?',
      dateFields: [
        ['ASEL COM training start', ''],
        ['ASEL COM checkride pass date', '']
      ]
    },
    {
      key: 'AMEL',
      title: 'Multi-Engine (AMEL)',
      gate: 'Did you complete your AMEL at Provectus?',
      dateFields: [
        ['AMEL training start', ''],
        ['AMEL checkride pass date', '']
      ]
    },
    {
      key: 'CFI',
      title: 'CFI',
      gate: 'Did you complete your initial CFI at Provectus?',
      dateFields: [
        ['CFI training start', ''],
        ['CFI checkride pass date', '']
      ]
    },
    {
      key: 'CFII',
      title: 'CFII',
      gate: 'Did you complete your CFII at Provectus?',
      dateFields: [
        ['CFII training start', ''],
        ['CFII checkride pass date', '']
      ]
    },
    {
      key: 'MEI',
      title: 'MEI',
      gate: 'Did you complete your MEI at Provectus?',
      dateFields: [
        ['MEI training start', ''],
        ['MEI checkride pass date', '']
      ]
    }
  ];

  // Linear build — page break, gate question, date items, for each rating.
  const builtPages = [];
  const builtGates = [];

  ratings.forEach((r) => {
    const page = form.addPageBreakItem().setTitle(r.title);
    builtPages.push(page);

    const gate = form.addMultipleChoiceItem()
      .setTitle(r.gate)
      .setRequired(true);
    builtGates.push(gate);

    r.dateFields.forEach(([title, help]) => {
      const item = form.addDateItem().setTitle(title).setIncludesYear(true);
      if (help) item.setHelpText(help);
    });
  });

  const wrapPage = form.addPageBreakItem().setTitle('Anything else');
  form.addParagraphTextItem()
    .setTitle('Anything we should know about your training timeline?')
    .setHelpText('E.g. gaps for medical, transfers in from another school, paused for finals — anything that explains an unusual stretch of dates.');

  // Wire up branching on each gate: "No" → skip to the NEXT rating's page (or wrap-up).
  ratings.forEach((r, idx) => {
    const gate = builtGates[idx];
    const nextTarget = (idx + 1 < ratings.length) ? builtPages[idx + 1] : wrapPage;
    gate.setChoices([
      gate.createChoice('Yes', FormApp.PageNavigationType.CONTINUE),
      gate.createChoice('No', nextTarget)
    ]);
  });

  Logger.log('Form created.');
  Logger.log('Edit URL: ' + form.getEditUrl());
  Logger.log('Live (responder) URL: ' + form.getPublishedUrl());
  Logger.log('Short URL: ' + form.shortenFormUrl(form.getPublishedUrl()));
}


// ============================================================================
// Prefilled-link generator
// ============================================================================
//
// After buildAlumniForm runs and you have the form's live URL, paste it into
// FORM_LIVE_URL below. Add recipients to the RECIPIENTS array. Run
// generatePrefilledLinks — it prints one personalized URL per recipient to
// the Execution log.
//
// Mail merge tools (Gmail, Mailmeteor, YAMM) can use these per-recipient URLs
// directly.

const FORM_LIVE_URL = ''; // e.g. 'https://docs.google.com/forms/d/e/.../viewform'

const RECIPIENTS = [
  { firstName: 'Olsen', lastName: 'Durkovich', email: 'olsen@provectusaviation.com' },
  { firstName: 'Andy',  lastName: 'Littlefield', email: 'andy@provectusaviation.com' }
];

function generatePrefilledLinks() {
  if (!FORM_LIVE_URL) {
    Logger.log('ERROR: set FORM_LIVE_URL at the top of this script to the form\'s live URL first.');
    return;
  }

  // Open the form by its URL and locate the Full name + Email items by title.
  const form = FormApp.openByUrl(FORM_LIVE_URL.replace('/viewform', '/edit'));
  const items = form.getItems(FormApp.ItemType.TEXT);
  const nameItem = items.find(i => i.getTitle() === 'Full name');
  const emailItem = items.find(i => i.getTitle() === 'Email');

  if (!nameItem || !emailItem) {
    Logger.log('ERROR: could not find the "Full name" or "Email" question on the form.');
    return;
  }

  RECIPIENTS.forEach(r => {
    const resp = form.createResponse();
    resp.withItemResponse(nameItem.asTextItem().createResponse(r.firstName + ' ' + r.lastName));
    resp.withItemResponse(emailItem.asTextItem().createResponse(r.email));
    const url = resp.toPrefilledUrl();
    Logger.log(r.firstName + ' ' + r.lastName + ' <' + r.email + '>: ' + url);
  });
}

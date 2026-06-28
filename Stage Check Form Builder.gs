/**
 * Provectus Stage Check Record — Google Form builder.
 *
 * HOW TO USE:
 *   1. Go to https://script.google.com  →  New project.
 *   2. Paste this whole file in, replacing the default code.
 *   3. Run buildStageCheckForm()  (authorize when prompted).
 *   4. The execution log prints the edit + live URLs. Open the edit URL,
 *      then Responses → link to a Google Sheet for the data feed.
 *
 * WHY IT'S SHAPED THIS WAY:
 *   A stage check is a dated, rating-tagged, phase-tagged event recorded live
 *   by an instructor — exactly the signal the analytics pipeline otherwise has
 *   to reconstruct heuristically. The Rating question branches to a
 *   rating-specific Stage question, so each response stamps the right milestone.
 *
 *   Required set is kept short (date, name, email, rating, stage, result) so
 *   instructors actually fill it out; the rest is optional but high-value.
 */
function buildStageCheckForm() {
  var form = FormApp.create('Provectus Stage Check Record')
    .setDescription(
      'Complete one entry every time a stage check is conducted. ' +
      'This feeds training-progress analytics, so accurate student email and ' +
      'date matter most.')
    .setCollectEmail(false)   // we want the STUDENT's email, asked below
    .setProgressBar(true);

  // ---- Page 1: identity + rating (the branch point) ----------------------
  form.addDateItem()
    .setTitle('Date of stage check')
    .setHelpText('The date the stage check actually happened (not today, if filling in later).')
    .setRequired(true)
    .setIncludesYear(true);

  form.addTextItem()
    .setTitle('Student full name')
    .setRequired(true);

  form.addTextItem()
    .setTitle('Student email')
    .setHelpText('Primary key for matching the student to their training records — please double-check it.')
    .setRequired(true);

  var rating = form.addMultipleChoiceItem()
    .setTitle('Rating in training')
    .setRequired(true);

  // ---- Section pages (created now so we can navigate to them) ------------
  var pplPage = form.addPageBreakItem().setTitle('PPL — stage check');
  var pplStage = form.addMultipleChoiceItem()
    .setTitle('Which stage check?')
    .setChoiceValues(['Pre-solo', 'Pre-cross-country (solo XC)', 'Pre-checkride (end of course)'])
    .setRequired(true);

  var ifrPage = form.addPageBreakItem().setTitle('IFR — stage check');
  var ifrStage = form.addMultipleChoiceItem()
    .setTitle('Which stage check?')
    .setChoiceValues(['Stage 1 — XC time complete', 'Stage 2 — pre-checkride'])
    .setRequired(true);

  var otherPage = form.addPageBreakItem().setTitle('Stage check');
  var otherStage = form.addMultipleChoiceItem()
    .setTitle('Which stage check?')
    .setChoiceValues(['Pre-checkride (end of course)'])
    .setRequired(true);

  // ---- Common details page (every path ends here) ------------------------
  var commonPage = form.addPageBreakItem().setTitle('Stage check details');

  form.addMultipleChoiceItem()
    .setTitle('Result')
    .setChoiceValues(['Satisfactory — proceed', 'Unsatisfactory — additional training', 'Partial / incomplete'])
    .setRequired(true);

  form.addTextItem()
    .setTitle('Total flight hours to date (Hobbs)')
    .setHelpText('Approximate is fine. Lets us cross-check hours at this milestone.');

  form.addTextItem()
    .setTitle('Conducting (stage-check) instructor');

  form.addTextItem()
    .setTitle("Student's primary CFI");

  form.addListItem()
    .setTitle('Aircraft flown')
    .setHelpText('Confirms single- vs multi-engine for rating attribution. Pick the family; sub-models do not matter.')
    .setChoiceValues(['C172', 'PA-28', 'BE-76', 'Other single-engine (ASEL)', 'Other multi-engine (AMEL)']);

  form.addParagraphTextItem()
    .setTitle('Notes / areas to improve (optional)');

  // ---- Wire the navigation -----------------------------------------------
  // Rating answer → the matching stage page.
  rating.setChoices([
    rating.createChoice('PPL', pplPage),
    rating.createChoice('IFR', ifrPage),
    rating.createChoice('ASEL COM', otherPage),
    rating.createChoice('AMEL', otherPage),
    rating.createChoice('CFI', otherPage),
    rating.createChoice('CFII', otherPage),
    rating.createChoice('MEI', otherPage)
  ]);

  // After each stage page, jump straight to the common details page.
  pplPage.setGoToPage(commonPage);
  ifrPage.setGoToPage(commonPage);
  otherPage.setGoToPage(commonPage);

  Logger.log('Edit URL: ' + form.getEditUrl());
  Logger.log('Live URL: ' + form.getPublishedUrl());
}

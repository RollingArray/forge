import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { test, expect } from '../workspace/workspace.fixtures';
import type { Page } from '@playwright/test';

const sections = [
  {
    name: 'Entities',
    fileName: '01_entities.csv',
    header: 'entity,description,population_count,population_scaling',
  },
  {
    name: 'Fields & Keys',
    fileName: '02_fields_and_keys.csv',
    header:
      'entity,field,type,identity_position,identity_strategy,generation_strategy,distribution,generator,minimum,maximum,minimum_length,maximum_length,character_set,pattern,semantic_description,semantic_mode,values',
  },
  {
    name: 'Foreign Keys',
    fileName: '03_foreign_keys.csv',
    header: 'source_entity,source_fields,target_entity',
  },
  {
    name: 'Relationships',
    fileName: '04_relationships.csv',
    header:
      'source_entity,target_entity,type,source_participation,target_participation',
  },
  {
    name: 'Constraints',
    fileName: '05_constraints.csv',
    header: 'entity,field,operator,value',
  },
];

function readCanonicalCsv(fileName: string): string {
  return readFileSync(
    resolve(
      __dirname,
      '../../public/assets/forge-samples/aerospace',
      fileName,
    ),
    'utf8',
  )
    .replace(/\r\n/g, '\n')
    .trimEnd();
}

async function getApiAuthorizationHeaders(
  page: Page,
): Promise<Record<string, string>> {
  const session = await page.evaluate(() => {
    const stored = localStorage.getItem('forge.auth.session');

    if (!stored) return null;

    try {
      const parsed = JSON.parse(stored);
      return {
        accessToken: parsed.accessToken,
        tokenType: parsed.tokenType,
      };
    } catch {
      return null;
    }
  });

  expect(session?.accessToken).toBeTruthy();
  expect(session?.tokenType).toBe('Bearer');

  return {
    Authorization: `${session!.tokenType} ${session!.accessToken}`,
  };
}

async function exportPersistedSpecification(
  page: Page,
  modelId: string,
): Promise<Record<string, string>> {
  const origin = new URL(page.url()).origin;
  const response = await page.context().request.get(
    `${origin}/api/v1/data-models/${modelId}/specification/replacement/export`,
    { headers: await getApiAuthorizationHeaders(page) },
  );

  expect(response.status()).toBe(200);
  return await response.json() as Record<string, string>;
}

type ReplacementCsv = {
  entities: string;
  fields_and_keys: string;
  foreign_keys: string;
  relationships: string;
  constraints: string;
};

function canonicalReplacementCsv(): ReplacementCsv {
  return {
    entities: readCanonicalCsv('01_entities.csv'),
    fields_and_keys: readCanonicalCsv('02_fields_and_keys.csv'),
    foreign_keys: readCanonicalCsv('03_foreign_keys.csv'),
    relationships: readCanonicalCsv('04_relationships.csv'),
    constraints: readCanonicalCsv('05_constraints.csv'),
  };
}

async function postReplacementPreview(
  page: Page,
  modelId: string,
  csv: ReplacementCsv,
) {
  const origin = new URL(page.url()).origin;
  return page.context().request.post(
    `${origin}/api/v1/data-models/${modelId}/specification/replacement/preview`,
    {
      headers: await getApiAuthorizationHeaders(page),
      data: { csv },
    },
  );
}

test.describe('MS21 - Specification Wizard navigation and state', () => {
  test.beforeEach(async ({ page, workspaceModel }, testInfo) => {
    test.setTimeout(120_000);

    await workspaceModel.card.click();

    await expect(page).toHaveURL(
      /\/workspace\/[^/]+\/model-studio$/,
    );

    const modelId = new URL(page.url()).pathname.split('/')[2];
    expect(modelId).toBeTruthy();

    await testInfo.attach('specification-replacement-model', {
      body: JSON.stringify({
        modelName: workspaceModel.name,
        modelId,
      }, null, 2),
      contentType: 'application/json',
    });

    await page.getByRole('button', {
      name: /CSV Specification/,
    }).click();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/specification-wizard$`),
    );

    await expect(
      page.getByRole('heading', {
        name: 'Define your Data Model',
        exact: true,
      }),
    ).toBeVisible();

    await page.getByRole('button', {
      name: 'Load Complete Aerospace Sample',
      exact: true,
    }).click();

    // Wait for all five asynchronous sample requests and conversion to finish.
    await expect(
      page.getByRole('status').filter({
        hasText: 'All five sample sections are ready for editing.',
      }),
    ).toBeVisible();

    // Verify the editor reflects the completed sample load.
    await expect(
      page.locator('#csv-section-input'),
    ).toHaveValue(readCanonicalCsv('01_entities.csv'));
  });

  test('MS21-01: Loads the selected model in the Specification Wizard', async ({
    page,
  }) => {
    const modelId = new URL(page.url()).pathname.split('/')[2];

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/specification-wizard$`),
    );

    await expect(
      page.getByRole('heading', {
        name: 'Define your Data Model',
        exact: true,
      }),
    ).toBeVisible();

    const textarea = page.locator('#csv-section-input');

    await expect(textarea).toHaveValue(readCanonicalCsv('01_entities.csv'));
  });

  test('MS21-02: Verifies canonical content for all five CSV sections', async ({
    page,
  }) => {
    const textarea = page.locator('#csv-section-input');

    for (const section of sections) {
      await page.getByRole('tab', {
        name: section.name,
        exact: true,
      }).click();

      await expect(textarea).toHaveValue(
        readCanonicalCsv(section.fileName),
      );
    }
  });

  test('MS21-03: Navigates between all five CSV sections', async ({
    page,
  }) => {
    const textarea = page.locator('#csv-section-input');
    let previousHeader: string | undefined;

    for (const section of sections) {
      await page.getByRole('tab', {
        name: section.name,
        exact: true,
      }).click();

      await expect.poll(async () => {
        const content = await textarea.inputValue();
        return content.split(/\r?\n/, 1)[0];
      }).toBe(section.header);

      if (previousHeader !== undefined) {
        expect(section.header).not.toBe(previousHeader);
      }

      previousHeader = section.header;
    }
  });

  test('MS21-04: Retains unsaved edits when switching between CSV sections', async ({
    page,
  }, testInfo) => {
    const textarea = page.locator('#csv-section-input');

    await page.getByRole('tab', {
      name: 'Entities',
      exact: true,
    }).click();

    const originalCsv = await textarea.inputValue();

    const editedCsv = originalCsv.replace(
      /\r?\n([^,\r\n]+)/,
      (_, entityName) => `\n${entityName}_MS21_EDIT`,
    );

    expect(editedCsv).not.toBe(originalCsv);

    await textarea.fill(editedCsv);
    await expect(textarea).toHaveValue(editedCsv);

    await page.getByRole('tab', {
      name: 'Fields & Keys',
      exact: true,
    }).click();

    await expect(textarea).not.toHaveValue(editedCsv);

    await page.getByRole('tab', {
      name: 'Entities',
      exact: true,
    }).click();

    await expect(textarea).toHaveValue(editedCsv);

    await testInfo.attach('ms21-edited-entities-csv', {
      body: editedCsv,
      contentType: 'text/csv',
    });
  });

  test('MS21-05: Preserves candidate CSV edits when returning from Model Validation', async ({
    page,
  }, testInfo) => {
    const textarea = page.locator('#csv-section-input');

    await page.getByRole('tab', {
      name: 'Entities',
      exact: true,
    }).click();

    const originalCsv = await textarea.inputValue();
    const lines = originalCsv.split(/\r?\n/);

    expect(lines.length).toBeGreaterThan(1);

    // Change the first entity description without changing its identity
    // or any relationship and foreign-key references.
    const firstDataRow = lines[1];
    const firstComma = firstDataRow.indexOf(',');
    const secondComma = firstDataRow.indexOf(',', firstComma + 1);

    expect(firstComma).toBeGreaterThan(0);
    expect(secondComma).toBeGreaterThan(firstComma);

    lines[1] =
      firstDataRow.slice(0, secondComma) +
      '_MS21_05_EDIT' +
      firstDataRow.slice(secondComma);

    const editedCsv = lines.join('\n');

    expect(editedCsv).not.toBe(originalCsv);

    await textarea.fill(editedCsv);
    await expect(textarea).toHaveValue(editedCsv);

    // Prepare the candidate and open canonical Model Validation.
    await page.getByRole('button', {
      name: /^Prepare replacement$/,
    }).click();

    const modelId = new URL(page.url()).pathname.split('/')[2];

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/model-validation$`),
      { timeout: 60_000 },
    );

    await expect(
      page.getByRole('heading', {
        name: 'Model Validation',
        exact: true,
      }),
    ).toBeVisible();

    // Return through the application's explicit candidate-preserving action.
    await page.getByRole('button', {
      name: 'Back to CSV Wizard',
      exact: true,
    }).click();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/specification-wizard$`),
    );

    // Router state must restore the exact candidate CSV, not persisted CSV.
    await expect(textarea).toHaveValue(editedCsv);

    await testInfo.attach('ms21-05-restored-entities-csv', {
      body: editedCsv,
      contentType: 'text/csv',
    });
  });

  test('MS21-06: Discards unapplied CSV edits when leaving the Wizard', async ({
    page,
  }, testInfo) => {
    const modelId = new URL(page.url()).pathname.split('/')[2];
    const textarea = page.locator('#csv-section-input');

    const persistedBefore = await exportPersistedSpecification(page, modelId);

    expect(Object.keys(persistedBefore).sort()).toEqual([
      'constraints',
      'entities',
      'fields_and_keys',
      'foreign_keys',
      'relationships',
    ]);

    await page.getByRole('tab', {
      name: 'Entities',
      exact: true,
    }).click();

    const originalCsv = await textarea.inputValue();
    const lines = originalCsv.split(/\r?\n/);

    expect(lines.length).toBeGreaterThan(1);

    const firstDataRow = lines[1];
    const firstComma = firstDataRow.indexOf(',');
    const secondComma = firstDataRow.indexOf(',', firstComma + 1);

    expect(firstComma).toBeGreaterThan(0);
    expect(secondComma).toBeGreaterThan(firstComma);

    lines[1] =
      firstDataRow.slice(0, secondComma) +
      '_MS21_06_UNAPPLIED' +
      firstDataRow.slice(secondComma);

    const editedCsv = lines.join('\n');

    expect(editedCsv).not.toBe(originalCsv);
    await textarea.fill(editedCsv);
    await expect(textarea).toHaveValue(editedCsv);

    // Leave without preparing or applying the replacement.
    await page.getByRole('button', {
      name: 'Back to Model Studio',
      exact: true,
    }).click();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/model-studio$`),
    );

    // Reopen the Wizard and confirm the persisted CSV is restored.
    await page.getByRole('button', {
      name: /CSV Specification/,
    }).click();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/specification-wizard$`),
    );

    await expect(
      page.getByRole('heading', {
        name: 'Define your Data Model',
        exact: true,
      }),
    ).toBeVisible();

    await page.getByRole('tab', {
      name: 'Entities',
      exact: true,
    }).click();

    await expect(textarea).toHaveValue(persistedBefore.entities);
    await expect(textarea).not.toHaveValue(editedCsv);

    const persistedAfter = await exportPersistedSpecification(page, modelId);
    expect(persistedAfter).toEqual(persistedBefore);

    await testInfo.attach('ms21-06-persisted-specification-before.json', {
      body: JSON.stringify(persistedBefore, null, 2),
      contentType: 'application/json',
    });

    await testInfo.attach('ms21-06-persisted-specification-after.json', {
      body: JSON.stringify(persistedAfter, null, 2),
      contentType: 'application/json',
    });
  });

  test('MS21-07: Reopens the Wizard with all persisted CSV sections', async ({
    page,
  }, testInfo) => {
    const modelId = new URL(page.url()).pathname.split('/')[2];

    // Capture the authoritative persisted CSV for all five sections.
    const persisted = await exportPersistedSpecification(page, modelId);

    expect(Object.keys(persisted).sort()).toEqual([
      'constraints',
      'entities',
      'fields_and_keys',
      'foreign_keys',
      'relationships',
    ]);

    // Leave the Wizard and reopen it without loading the sample again.
    await page.getByRole('button', {
      name: 'Back to Model Studio',
      exact: true,
    }).click();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/model-studio$`),
    );

    await page.getByRole('button', {
      name: /CSV Specification/,
    }).click();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/specification-wizard$`),
    );

    await expect(
      page.getByRole('heading', {
        name: 'Define your Data Model',
        exact: true,
      }),
    ).toBeVisible();

    const textarea = page.locator('#csv-section-input');
    const persistedSections = [
      { name: 'Entities', key: 'entities' },
      { name: 'Fields & Keys', key: 'fields_and_keys' },
      { name: 'Foreign Keys', key: 'foreign_keys' },
      { name: 'Relationships', key: 'relationships' },
      { name: 'Constraints', key: 'constraints' },
    ] as const;

    for (const section of persistedSections) {
      await page.getByRole('tab', {
        name: section.name,
        exact: true,
      }).click();

      await expect(textarea).toHaveValue(persisted[section.key]);
    }

    // Confirm that reopening the Wizard did not modify persisted content.
    const persistedAfter = await exportPersistedSpecification(page, modelId);
    expect(persistedAfter).toEqual(persisted);

    await testInfo.attach('ms21-07-persisted-specification.json', {
      body: JSON.stringify(persisted, null, 2),
      contentType: 'application/json',
    });
  });

  test('MS21-08: Prepares a replacement candidate and opens Model Validation', async ({
    page,
  }, testInfo) => {
    const modelId = new URL(page.url()).pathname.split('/')[2];
    const textarea = page.locator('#csv-section-input');

    // Confirm the complete Aerospace sample is loaded before preparation.
    for (const section of sections) {
      await page.getByRole('tab', {
        name: section.name,
        exact: true,
      }).click();

      await expect(textarea).toHaveValue(
        readCanonicalCsv(section.fileName),
      );
    }

    // Prepare the candidate without applying it.
    await page.getByRole('button', {
      name: /^Prepare replacement$/,
    }).click();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/model-validation$`),
      { timeout: 60_000 },
    );

    await expect(
      page.getByRole('heading', {
        name: 'Model Validation',
        exact: true,
      }),
    ).toBeVisible();

    // A valid candidate should be eligible for confirmation.
    // Do not click this button: applying the replacement belongs to MS24.
    const confirmButton = page.getByRole('button', {
      name: 'Confirm replacement',
      exact: true,
    });

    await expect(confirmButton).toBeVisible();
    await expect(confirmButton).toBeEnabled();

    await testInfo.attach('ms21-08-prepared-candidate.json', {
      body: JSON.stringify({
        modelId,
        modelValidationUrl: page.url(),
        candidatePrepared: true,
        confirmationEnabled: true,
        replacementApplied: false,
      }, null, 2),
      contentType: 'application/json',
    });
  });

  test('MS22-01: Accepts all five required CSV sections with valid headers', async ({
    page,
  }, testInfo) => {
    const modelId = new URL(page.url()).pathname.split('/')[2];
    const persistedBefore = await exportPersistedSpecification(page, modelId);

    const previewResponsePromise = page.waitForResponse((response) =>
      response.url().includes(
        `/api/v1/data-models/${modelId}/specification/replacement/preview`,
      ) && response.request().method() === 'POST',
    );

    await page.getByRole('button', {
      name: /^Prepare replacement$/,
    }).click();

    const previewResponse = await previewResponsePromise;
    expect(previewResponse.status()).toBe(200);

    const preview = await previewResponse.json() as {
      can_apply: boolean;
      issues: unknown[];
      summary: Record<string, number>;
      validation: unknown;
      candidate: unknown;
    };

    expect(preview.can_apply).toBe(true);
    expect(preview.issues).toEqual([]);
    expect(preview.validation).toBeNull();
    expect(preview.candidate).toBeTruthy();

    for (const section of [
      'entities',
      'fields_and_keys',
      'foreign_keys',
      'relationships',
      'constraints',
    ]) {
      expect(
        preview.summary[section],
        `Expected a numeric summary for ${section}`,
      ).toEqual(expect.any(Number));
      expect(preview.summary[section]).toBeGreaterThanOrEqual(0);
    }

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/model-validation$`),
      { timeout: 60_000 },
    );

    await expect(
      page.getByRole('heading', {
        name: 'Model Validation',
        exact: true,
      }),
    ).toBeVisible();

    const persistedAfter = await exportPersistedSpecification(page, modelId);
    expect(persistedAfter).toEqual(persistedBefore);

    await testInfo.attach('ms22-01-valid-replacement-preview.json', {
      body: JSON.stringify({
        modelId,
        status: previewResponse.status(),
        canApply: preview.can_apply,
        issues: preview.issues,
        summary: preview.summary,
        canonicalValidationInvoked: preview.validation !== null,
        replacementApplied: false,
        persistedSpecificationUnchanged: true,
      }, null, 2),
      contentType: 'application/json',
    });
  });

  test('MS22-02: Reports missing required CSV headers', async ({
    page,
  }, testInfo) => {
    const modelId = new URL(page.url()).pathname.split('/')[2];
    const persistedBefore = await exportPersistedSpecification(page, modelId);
    const editor = page.locator('#csv-section-input');

    const invalidCsv = [
      'description,population_count,population_scaling',
      'Airlines and aerospace manufacturers,40,SCALABLE',
    ].join('\n');

    await editor.fill(invalidCsv);

    const responsePromise = page.waitForResponse((response) =>
      response.url().includes(
        `/api/v1/data-models/${modelId}/specification/replacement/preview`,
      ) && response.request().method() === 'POST',
    );

    await page.getByRole('button', {
      name: /^Prepare replacement$/,
    }).click();

    const response = await responsePromise;
    expect(response.status()).toBe(200);

    const preview = await response.json();
    expect(preview.can_apply).toBe(false);
    expect(preview.candidate).toBeNull();
    expect(preview.issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          section: 'entities',
          row: 1,
          column: 'entity',
        }),
      ]),
    );

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/specification-wizard$`),
    );

    const review = page.locator('[aria-label="CSV replacement review"]');
    await expect(review).toBeVisible();
    await expect(review).toContainText('Needs attention');
    await expect(review).toContainText('column: entity');

    await expect(editor).toHaveValue(invalidCsv);

    const persistedAfter = await exportPersistedSpecification(page, modelId);
    expect(persistedAfter).toEqual(persistedBefore);

    await testInfo.attach('ms22-02-missing-header-review.json', {
      body: JSON.stringify({
        modelId,
        canApply: preview.can_apply,
        issues: preview.issues,
        editorRetained: true,
        persistedSpecificationUnchanged: true,
      }, null, 2),
      contentType: 'application/json',
    });
  });
  test('MS22-03: Reports unexpected CSV columns', async ({
    page,
  }, testInfo) => {
    const modelId = new URL(page.url()).pathname.split('/')[2];
    const persistedBefore = await exportPersistedSpecification(page, modelId);
    const editor = page.locator('#csv-section-input');

    await page.getByRole('tab', {
      name: 'Constraints',
      exact: true,
    }).click();

    const originalCsv = await editor.inputValue();
    const lines = originalCsv.split(/\r?\n/);

    lines[0] = `${lines[0]},unexpected_column`;
    const invalidCsv = [
      lines[0],
      ...lines.slice(1).map((line) => `${line},`),
    ].join('\n');

    await editor.fill(invalidCsv);

    const responsePromise = page.waitForResponse((response) =>
      response.url().includes(
        `/api/v1/data-models/${modelId}/specification/replacement/preview`,
      ) && response.request().method() === 'POST',
    );

    await page.getByRole('button', {
      name: /^Prepare replacement$/,
    }).click();

    const response = await responsePromise;
    expect(response.status()).toBe(200);

    const preview = await response.json();
    expect(preview.can_apply).toBe(false);
    expect(preview.candidate).toBeNull();
    expect(preview.issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          section: 'constraints',
          row: 1,
          column: 'unexpected_column',
        }),
      ]),
    );

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/specification-wizard$`),
    );

    const review = page.locator('[aria-label="CSV replacement review"]');
    await expect(review).toBeVisible();
    await expect(review).toContainText('Needs attention');
    await expect(review).toContainText('unexpected_column');

    await expect(editor).toHaveValue(invalidCsv);

    const persistedAfter = await exportPersistedSpecification(page, modelId);
    expect(persistedAfter).toEqual(persistedBefore);

    await testInfo.attach('ms22-03-unexpected-column-review.json', {
      body: JSON.stringify({
        modelId,
        canApply: preview.can_apply,
        issues: preview.issues,
        editorRetained: true,
        persistedSpecificationUnchanged: true,
      }, null, 2),
      contentType: 'application/json',
    });
  });
  test('MS22-04: Rejects malformed quoting before candidate preparation', async ({
    page,
  }, testInfo) => {
    const modelId = new URL(page.url()).pathname.split('/')[2];
    const csv = canonicalReplacementCsv();
    const editor = page.locator('#csv-section-input');

    // Wait until the shared MS21 setup has finished loading the Aerospace sample.
    await expect(editor).toHaveValue(
      readCanonicalCsv('01_entities.csv'),
    );

    csv.entities = [
      'entity,description,population_count,population_scaling',
      '"CUSTOMER,Malformed description,40,SCALABLE',
    ].join('\n');

    // Enter malformed CSV only after sample loading has completed.
    await editor.fill(csv.entities);
    await expect(editor).toHaveValue(csv.entities);

    const parseAlert = page.getByRole('alert');

    await expect(parseAlert).toContainText(
      'CSV formatting needs attention',
    );

    const prepareButton = page.getByRole('button', {
      name: /^Prepare replacement$/,
    });

    await expect(prepareButton).toBeDisabled();

    // A malformed CSV must not trigger a preview request.
    const previewRequests = page.waitForRequest(
      (request) =>
        request.url().includes(
          `/api/v1/data-models/${modelId}/specification/replacement/preview`,
        ) && request.method() === 'POST',
      { timeout: 2000 },
    ).then(
      () => true,
      (error) => {
        if (error.name === 'TimeoutError') {
          return false;
        }
        throw error;
      },
    );

    expect(await previewRequests).toBe(false);

    const preview = await postReplacementPreview(page, modelId, csv)
      .then(async (response) => {
        expect(response.status()).toBe(200);
        return response.json();
      });
    expect(preview.can_apply).toBe(false);
    expect(preview.candidate).toBeNull();
    expect(preview.issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          section: 'entities',
          row: expect.any(Number),
          column: null,
          message: expect.stringContaining('Invalid CSV syntax'),
        }),
      ]),
    );

    await testInfo.attach('ms22-04-malformed-quoting-diagnostics.json', {
      body: JSON.stringify(preview.issues, null, 2),
      contentType: 'application/json',
    });
  });

  test('MS22-05: Reports invalid basic type conversions', async ({
    page,
  }, testInfo) => {
    const modelId = new URL(page.url()).pathname.split('/')[2];
    const persistedBefore = await exportPersistedSpecification(page, modelId);
    const editor = page.locator('#csv-section-input');

    const invalidCsv = readCanonicalCsv('01_entities.csv').replace(
      'CUSTOMER,Airlines and aerospace manufacturers,40,SCALABLE',
      'CUSTOMER,Airlines and aerospace manufacturers,not-a-number,SCALABLE',
    );

    await editor.fill(invalidCsv);

    // Confirm the browser editor retained the intended value before preview.
    await expect(editor).toHaveValue(invalidCsv);


    const responsePromise = page.waitForResponse((response) =>
      response.url().includes(
        `/api/v1/data-models/${modelId}/specification/replacement/preview`,
      ) && response.request().method() === 'POST',
    );

    await page.getByRole('button', {
      name: /^Prepare replacement$/,
    }).click();

    const response = await responsePromise;
    expect(response.status()).toBe(200);

    const preview = await response.json();

    const submittedCsv = response.request().postDataJSON() as {
      csv: Record<string, string>;
    };

    console.log(
      '[MS22-05] Submitted entities CSV:',
      JSON.stringify(submittedCsv.csv.entities),
    );

    console.log(
      '[MS22-05] Preview response:',
      JSON.stringify({
        can_apply: preview.can_apply,
        candidate_is_null: preview.candidate === null,
        issues: preview.issues,
      }),
    );

    expect(preview.can_apply).toBe(false);
    expect(preview.candidate).toBeNull();
    expect(preview.issues).toEqual([
      expect.objectContaining({
        section: 'entities',
        row: 2,
        column: 'population_count',
        message: 'population_count must be a whole number.',
      }),
    ]);

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/specification-wizard$`),
    );

    const review = page.locator('[aria-label="CSV replacement review"]');
    await expect(review).toBeVisible();
    await expect(review).toContainText('Needs attention');
    await expect(review).toContainText('population_count');
    await expect(review).toContainText(
      'population_count must be a whole number.',
    );

    await expect(editor).toHaveValue(invalidCsv);

    const persistedAfter = await exportPersistedSpecification(page, modelId);
    expect(persistedAfter).toEqual(persistedBefore);

    await testInfo.attach('ms22-05-type-conversion-review.json', {
      body: JSON.stringify({
        modelId,
        canApply: preview.can_apply,
        issues: preview.issues,
        editorRetained: true,
        persistedSpecificationUnchanged: true,
      }, null, 2),
      contentType: 'application/json',
    });
  });
  test('MS22-06: Collects diagnostics for multiple malformed rows', async ({
    page,
  }, testInfo) => {
    const modelId = new URL(page.url()).pathname.split('/')[2];
    const csv = canonicalReplacementCsv();

    csv.entities = [
      'entity,description,population_count,population_scaling',
      'CUSTOMER,Malformed row,40,SCALABLE,unexpected',
      'AIRCRAFT_PROGRAM,Malformed row,12',
    ].join('\n');

    const response = await postReplacementPreview(page, modelId, csv);
    expect(response.status()).toBe(200);

    const preview = await response.json();
    expect(preview.can_apply).toBe(false);
    expect(preview.candidate).toBeNull();

    const entityIssues = preview.issues.filter(
      (issue: { section: string }) => issue.section === 'entities',
    );

    expect(entityIssues).toHaveLength(2);
    expect(entityIssues.map(
      (issue: { row: number }) => issue.row,
    )).toEqual([2, 3]);
    expect(entityIssues.every(
      (issue: { column: string | null }) => issue.column === null,
    )).toBe(true);

    await testInfo.attach('ms22-06-multiple-row-diagnostics.json', {
      body: JSON.stringify(preview.issues, null, 2),
      contentType: 'application/json',
    });
  });

  test('MS22-07: Blocks candidate preparation when conversion has errors', async ({
    page,
  }, testInfo) => {
    const modelId = new URL(page.url()).pathname.split('/')[2];
    const persistedBefore = await exportPersistedSpecification(page, modelId);

    const invalidEntities = readCanonicalCsv('01_entities.csv').replace(
      'CUSTOMER,Airlines and aerospace manufacturers,40,SCALABLE',
      'CUSTOMER,Airlines and aerospace manufacturers,-1,SCALABLE',
    );

    await page.locator('#csv-section-input').fill(invalidEntities);

    const responsePromise = page.waitForResponse((response) =>
      response.url().includes(
        `/api/v1/data-models/${modelId}/specification/replacement/preview`,
      ) && response.request().method() === 'POST',
    );

    await page.getByRole('button', {
      name: /^Prepare replacement$/,
    }).click();

    const response = await responsePromise;
    expect(response.status()).toBe(200);

    const preview = await response.json();

    const submittedCsv = response.request().postDataJSON() as {
      csv: Record<string, string>;
    };

    console.log(
      '[MS22-07] Submitted entities CSV:',
      JSON.stringify(submittedCsv.csv.entities),
    );

    console.log(
      '[MS22-07] Preview response:',
      JSON.stringify({
        can_apply: preview.can_apply,
        candidate_is_null: preview.candidate === null,
        issues: preview.issues,
      }),
    );

    expect(preview.can_apply).toBe(false);
    expect(preview.candidate).toBeNull();
    expect(preview.issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          section: 'entities',
          row: 2,
          column: 'population_count',
          message: 'population_count cannot be negative.',
        }),
      ]),
    );

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/specification-wizard$`),
    );

    const persistedAfter = await exportPersistedSpecification(page, modelId);
    expect(persistedAfter).toEqual(persistedBefore);

    await testInfo.attach('ms22-07-candidate-blocked.json', {
      body: JSON.stringify({
        modelId,
        canApply: preview.can_apply,
        candidatePresent: preview.candidate !== null,
        issues: preview.issues,
        persistedSpecificationUnchanged: true,
      }, null, 2),
      contentType: 'application/json',
    });
  });

  test('MS22-08: Corrects invalid CSV and successfully retries replacement preview', async ({
    page,
  }, testInfo) => {
    const modelId = new URL(page.url()).pathname.split('/')[2];
    const persistedBefore = await exportPersistedSpecification(page, modelId);

    const invalidEntities = readCanonicalCsv('01_entities.csv').replace(
      'CUSTOMER,Airlines and aerospace manufacturers,40,SCALABLE',
      'CUSTOMER,Airlines and aerospace manufacturers,invalid,SCALABLE',
    );

    const editor = page.locator('#csv-section-input');

    // Wait until the shared setup has finished loading the Aerospace sample.
    await expect(editor).toHaveValue(
      readCanonicalCsv('01_entities.csv'),
    );

    // Enter the invalid value only after sample loading is complete.
    await editor.fill(invalidEntities);
    await expect(editor).toHaveValue(invalidEntities);

    const firstResponsePromise = page.waitForResponse((response) =>
      response.url().includes(
        `/api/v1/data-models/${modelId}/specification/replacement/preview`,
      ) && response.request().method() === 'POST',
    );

    await page.getByRole('button', {
      name: /^Prepare replacement$/,
    }).click();

    const firstResponse = await firstResponsePromise;
    expect(firstResponse.status()).toBe(200);

    const firstPreview = await firstResponse.json();

    const submittedCsv = firstResponse.request().postDataJSON() as {
      csv: Record<string, string>;
    };

    console.log(
      '[MS22-08] Submitted entities CSV:',
      JSON.stringify(submittedCsv.csv.entities),
    );

    console.log(
      '[MS22-08] First preview response:',
      JSON.stringify({
        can_apply: firstPreview.can_apply,
        candidate_is_null: firstPreview.candidate === null,
        issues: firstPreview.issues,
      }),
    );

    expect(firstPreview.can_apply).toBe(false);
    expect(firstPreview.candidate).toBeNull();
    expect(firstPreview.issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          section: 'entities',
          row: 2,
          column: 'population_count',
        }),
      ]),
    );

    await editor.fill(readCanonicalCsv('01_entities.csv'));

    const retryResponsePromise = page.waitForResponse((response) =>
      response.url().includes(
        `/api/v1/data-models/${modelId}/specification/replacement/preview`,
      ) && response.request().method() === 'POST',
    );

    await page.getByRole('button', {
      name: /^Prepare replacement$/,
    }).click();

    const retryResponse = await retryResponsePromise;
    expect(retryResponse.status()).toBe(200);

    const retryPreview = await retryResponse.json();
    expect(retryPreview.can_apply).toBe(true);
    expect(retryPreview.issues).toEqual([]);
    expect(retryPreview.candidate).toBeTruthy();

    await expect(page).toHaveURL(
      new RegExp(`/workspace/${modelId}/model-validation$`),
      { timeout: 60_000 },
    );

    const persistedAfter = await exportPersistedSpecification(page, modelId);
    expect(persistedAfter).toEqual(persistedBefore);

    await testInfo.attach('ms22-08-corrected-retry.json', {
      body: JSON.stringify({
        modelId,
        firstAttemptCanApply: firstPreview.can_apply,
        firstAttemptIssues: firstPreview.issues,
        retryCanApply: retryPreview.can_apply,
        retryIssues: retryPreview.issues,
        replacementApplied: false,
        persistedSpecificationUnchanged: true,
      }, null, 2),
      contentType: 'application/json',
    });
  });

});

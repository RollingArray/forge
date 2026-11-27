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
});

import { test, expect, BrowserContext, Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const ENTITY = 'TestRecord';
const TARGET_ROWS = 12;
const BASE_URL =
  process.env.FORGE_E2E_BASE_URL ?? 'http://127.0.0.1:18876';

const AUTH_FILE = resolve(
  __dirname,
  '../../playwright/.auth/isolated-owner.json',
);

interface GeneratedPage {
  entity_name: string;
  filename: string;
  columns: string[];
  rows: Record<string, string | null>[];
  total_rows: number;
  offset: number;
  limit: number;
  search: string;
}

interface SpecificationField {
  name: string;
  type: string;
  identity?: Record<string, unknown>;
  generation?: {
    strategy?: string;
    distribution?: string;
    generator?: string;
    parameters?: Record<string, unknown>;
  };
}

interface Scenario {
  modelId: string;
  modelName: string;
  modelUrl: string;
  jobId: string;
  generatedData: GeneratedPage;
}

let setupContext: BrowserContext | undefined;
let scenario: Scenario | undefined;
let createdModelName: string | undefined;

function requireScenario(): Scenario {
  if (!scenario) {
    throw new Error('MS08 shared generation scenario was not initialized.');
  }
  return scenario;
}

function fieldCsv(
  field: string,
  type: string,
  options: Record<string, string> = {},
): string {
  const columns = [
    'entity',
    'field',
    'type',
    'identity_position',
    'identity_strategy',
    'generation_strategy',
    'distribution',
    'generator',
    'minimum',
    'maximum',
    'minimum_length',
    'maximum_length',
    'character_set',
    'pattern',
    'semantic_description',
    'semantic_mode',
    'values',
  ];

  const values: Record<string, string> = {
    entity: ENTITY,
    field,
    type,
    ...options,
  };

  return columns.map((column) => {
    const value = values[column] ?? '';
    return /[",\r\n]/.test(value)
      ? `"${value.replace(/"/g, '""')}"`
      : value;
  }).join(',');
}

async function getApiAuthorizationHeaders(
  page: Page,
): Promise<Record<string, string>> {
  const session = await page.evaluate(() => {
    const stored = localStorage.getItem('forge.auth.session');

    if (!stored) {
      return null;
    }

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

  expect(
    session?.accessToken,
    'Authenticated E2E session should contain an access token',
  ).toBeTruthy();
  expect(session?.tokenType).toBe('Bearer');

  return {
    Authorization: `${session!.tokenType} ${session!.accessToken}`,
  };
}

async function getCanonicalFields(
  page: Page,
  modelId: string,
): Promise<SpecificationField[]> {
  const origin = new URL(page.url()).origin;
  const response = await page.context().request.get(
    `${origin}/api/v1/data-models/${modelId}/specification`,
    { headers: await getApiAuthorizationHeaders(page) },
  );

  expect(response.status()).toBe(200);

  const specification = await response.json() as {
    entities?: Array<{
      name: string;
      fields: SpecificationField[];
    }>;
  };

  const entity = specification.entities?.find(
    (item) => item.name === ENTITY,
  );

  expect(entity, `${ENTITY} should exist in the specification`).toBeTruthy();
  return entity!.fields;
}

async function createScenarioModel(page: Page): Promise<{
  modelId: string;
  modelName: string;
  modelUrl: string;
}> {
  const uniqueId =
    `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const modelName = `FORGE MS08 E2E ${uniqueId}`;
  await page.goto('/workspace');
  await expect(page.locator('app-workspace')).toBeVisible();

  await page.locator('.create-dataModel-card').click();

  const dialog = page.getByRole('dialog', { name: 'New Data Model' });
  await expect(dialog).toBeVisible();
  await page.locator('#data-model-name').fill(modelName);
  await page.locator('#data-model-description').fill(
    `MS08 shared field generation scenario ${uniqueId}`,
  );

  const saveButton = dialog.locator('button.save-button');
  await expect(saveButton).toBeEnabled();
  await saveButton.click();

  await expect(page).toHaveURL(
    /\/workspace\/[^/]+\/model-studio$/,
    { timeout: 30_000 },
  );

  const modelUrl = page.url();
  const match = modelUrl.match(
    /\/workspace\/([^/]+)\/model-studio$/,
  );

  expect(match, 'Expected model ID in Model Studio URL').not.toBeNull();

  return {
    modelId: match![1],
    modelName,
    modelUrl,
  };
}

async function importGenerationSpecification(
  page: Page,
  modelId: string,
): Promise<void> {
  await page.getByRole('button', { name: /CSV Specification/ }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelId}/specification-wizard$`),
  );

  await page.getByRole('tab', {
    name: 'Entities',
    exact: true,
  }).click();

  await page.locator('#csv-section-input').fill([
    'entity,description,population_count,population_scaling',
    `${ENTITY},MS08 field generation test entity,${TARGET_ROWS},FIXED`,
  ].join('\n'));

  await page.getByRole('tab', {
    name: 'Fields & Keys',
    exact: true,
  }).click();

  const fields = [
    [
      'entity', 'field', 'type', 'identity_position',
      'identity_strategy', 'generation_strategy', 'distribution',
      'generator', 'minimum', 'maximum', 'minimum_length',
      'maximum_length', 'character_set', 'pattern',
      'semantic_description', 'semantic_mode', 'values',
    ].join(','),

    fieldCsv('RECORD_ID', 'IDENTIFIER', {
      identity_position: '1',
      identity_strategy: 'SEQUENTIAL_ID',
    }),
    fieldCsv('RANDOM_TEXT', 'STRING', {
      generation_strategy: 'RANDOM',
      generator: 'RANDOM_STRING',
      minimum_length: '5',
      maximum_length: '10',
      character_set: 'ALPHANUMERIC',
    }),
    fieldCsv('ALPHA_TEXT', 'STRING', {
      generation_strategy: 'RANDOM',
      generator: 'RANDOM_STRING',
      minimum_length: '8',
      maximum_length: '8',
      character_set: 'ALPHA',
    }),
    fieldCsv('DIGITS_TEXT', 'STRING', {
      generation_strategy: 'RANDOM',
      generator: 'RANDOM_STRING',
      minimum_length: '8',
      maximum_length: '8',
      character_set: 'DIGITS',
    }),
    fieldCsv('ALNUM_TEXT', 'STRING', {
      generation_strategy: 'RANDOM',
      generator: 'RANDOM_STRING',
      minimum_length: '8',
      maximum_length: '8',
      character_set: 'ALPHANUMERIC',
    }),
    fieldCsv('BOUNDED_TEXT', 'STRING', {
      generation_strategy: 'RANDOM',
      generator: 'RANDOM_STRING',
      minimum_length: '6',
      maximum_length: '12',
      character_set: 'ALPHANUMERIC',
    }),
    fieldCsv('TOKEN_PATTERN', 'STRING', {
      generation_strategy: 'RANDOM',
      generator: 'PATTERN',
      pattern: 'ORD-#AA-aa-XX',
    }),
    fieldCsv('LITERAL_PATTERN', 'STRING', {
      generation_strategy: 'RANDOM',
      generator: 'PATTERN',
      pattern: 'INV-####-US',
    }),
    fieldCsv('INTEGER_UNIFORM', 'INTEGER', {
      generation_strategy: 'RANDOM',
      distribution: 'UNIFORM',
      minimum: '10',
      maximum: '20',
    }),
    fieldCsv('INTEGER_DISCRETE', 'INTEGER', {
      generation_strategy: 'RANDOM',
      distribution: 'DISCRETE_UNIFORM',
      minimum: '100',
      maximum: '200',
    }),
    fieldCsv('DECIMAL_UNIFORM', 'DECIMAL', {
      generation_strategy: 'RANDOM',
      distribution: 'UNIFORM',
      minimum: '1.00',
      maximum: '9.99',
    }),
    fieldCsv('DECIMAL_NORMAL', 'DECIMAL', {
      generation_strategy: 'RANDOM',
      distribution: 'NORMAL',
      minimum: '1.00',
      maximum: '9.99',
    }),
    fieldCsv('UNIQUE_DESCRIPTION', 'STRING', {
      generation_strategy: 'RANDOM',
      generator: 'SEMANTIC',
      semantic_description:
        'A distinct engineering component description for an aerospace manufacturing record',
      semantic_mode: 'UNIQUE',
    }),
    fieldCsv('PRODUCT_CATEGORY', 'STRING', {
      generation_strategy: 'RANDOM',
      generator: 'SEMANTIC',
      semantic_description:
        'A category of aerospace manufacturing components or systems',
      semantic_mode: 'VOCABULARY',
    }),
    fieldCsv('IS_ACTIVE', 'BOOLEAN', {
      generation_strategy: 'RANDOM',
    }),
    fieldCsv('PRODUCT_TIER', 'CATEGORICAL', {
      generation_strategy: 'RANDOM',
      distribution: 'CATEGORICAL',
      values: '["Bronze","Silver","Gold"]',
    }),
  ];

  await page.locator('#csv-section-input').fill(fields.join('\n'));

  const emptySections: Record<string, string> = {
    'Foreign Keys': 'source_entity,source_fields,target_entity',
    Relationships:
      'source_entity,target_entity,type,source_participation,target_participation',
    Constraints: 'entity,field,operator,value',
  };

  for (const [section, csv] of Object.entries(emptySections)) {
    await page.getByRole('tab', {
      name: section,
      exact: true,
    }).click();
    await page.locator('#csv-section-input').fill(csv);
  }

  await page.getByRole('button', {
    name: /^Preview CSV import$/,
  }).click();

  const review = page.locator('section[aria-label="CSV import review"]');
  await expect(review).toBeVisible();
  await expect(
    review.getByText('Ready to apply', { exact: true }),
  ).toBeVisible({ timeout: 60_000 });

  await page.getByRole('button', {
    name: /Apply additions & open Model Studio/,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelId}/model-studio$`),
    { timeout: 60_000 },
  );
}

async function addDecimalGridField(page: Page): Promise<void> {
  const entityNode = page
    .locator('app-model-studio-entity-node')
    .filter({ hasText: ENTITY });

  await expect(entityNode).toHaveCount(1);
  await entityNode.click();

  const inspector = page.locator('app-model-studio-entity-inspector');
  await inspector.getByRole('button', {
    name: 'Fields',
    exact: true,
  }).click();

  const addButton = inspector.locator(
    'app-inspector-fields .inspector-action, app-inspector-fields .empty-action',
  );

  await expect(addButton).toBeVisible();
  await addButton.click();

  const dialog = page.getByRole('dialog', {
    name: 'Add Field',
    exact: true,
  });

  await expect(dialog).toBeVisible();
  await dialog.locator('#field-name').fill('DECIMAL_GRID');

  await dialog.locator(
    'app-choice-card:has(strong:text-is("Decimal Number")) button.choice-card',
  ).click();

  await dialog.locator(
    'app-choice-card:has(strong:text-is("Evenly Distributed")) button.choice-card',
  ).click();

  await dialog.locator('#minimum').fill('1.00');
  await dialog.locator('#maximum').fill('9.99');
  await dialog.locator('#decimal-precision').fill('6');
  await dialog.locator('#decimal-scale').fill('2');

  const saveButton = dialog.locator('.save-button');
  await expect(saveButton).toBeEnabled();
  await saveButton.click();
  await expect(dialog).not.toBeVisible();
}

async function openCategoricalFieldDialog(
  page: Page,
): Promise<import('@playwright/test').Locator> {
  const entityNode = page
    .locator('app-model-studio-entity-node')
    .filter({ hasText: ENTITY });

  await expect(entityNode).toHaveCount(1);
  await entityNode.click();

  const inspector = page.locator('app-model-studio-entity-inspector');
  await inspector.getByRole('button', {
    name: 'Fields',
    exact: true,
  }).click();

  const addButton = inspector.locator(
    'app-inspector-fields .inspector-action, app-inspector-fields .empty-action',
  );

  await expect(addButton).toBeVisible();
  await addButton.click();

  const dialog = page.getByRole('dialog', {
    name: 'Add Field',
    exact: true,
  });

  await expect(dialog).toBeVisible();
  return dialog;
}

function numericValues(
  rows: Record<string, string | null>[],
  field: string,
): number[] {
  return rows.map((row) => {
    const raw = row[field];
    expect(raw, `${field} should have a generated value`).not.toBeNull();

    const value = Number(raw);
    expect(Number.isFinite(value), `${field} should be numeric`).toBe(true);
    return value;
  });
}

async function prepareScenario(
  browser: import('@playwright/test').Browser,
): Promise<void> {
  setupContext = await browser.newContext({
    baseURL: BASE_URL,
    storageState: AUTH_FILE,
  });

  const page = await setupContext.newPage();

  const model = await createScenarioModel(page);
  createdModelName = model.modelName;

  await importGenerationSpecification(page, model.modelId);
  await addDecimalGridField(page);

  const fields = await getCanonicalFields(page, model.modelId);
  expect(fields.find((field) => field.name === 'DECIMAL_GRID')).toBeTruthy();

  await page.getByRole('button', {
    name: 'Continue to Validation',
    exact: true,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${model.modelId}/model-validation$`),
  );

  await expect(
    page.getByText('Ready for Population', { exact: true }),
  ).toBeVisible({ timeout: 60_000 });

  await page.getByRole('button', {
    name: 'Continue to Population',
    exact: true,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${model.modelId}/data-model/population$`),
  );

  await expect(
    page.getByRole('heading', {
      name: 'Population Plan',
      exact: true,
    }),
  ).toBeVisible();

  await expect(page.locator('#population-target')).toBeVisible();

  await page.getByRole('button', {
    name: 'Review & Accept Plan',
    exact: true,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${model.modelId}/data-model/generate$`),
    { timeout: 60_000 },
  );

  await page.getByRole('button', {
    name: 'Start Generation',
    exact: true,
  }).click();

  await expect(
    page.getByText('Generation completed', { exact: true }),
  ).toBeVisible({ timeout: 240_000 });

  await page.getByRole('button', {
    name: 'Continue to Results',
    exact: true,
  }).click();

  await expect(page).toHaveURL(
    new RegExp(
      `/workspace/${model.modelId}/data-model/results/[^/]+$`,
    ),
    { timeout: 60_000 },
  );

  const resultsPath = new URL(page.url()).pathname;
  const jobMatch = resultsPath.match(/\/data-model\/results\/([^/]+)/);

  expect(jobMatch, 'Expected generation job ID in Results URL').not.toBeNull();

  const responsePromise = page.waitForResponse((response) => {
    const url = response.url();
    return response.status() === 200 &&
      url.includes('/artifacts/') &&
      url.includes('/data?');
  }, { timeout: 60_000 });

  await page.getByRole('button', {
    name: 'View full dataset',
    exact: true,
  }).click();

  const response = await responsePromise;
  const generatedData = await response.json() as GeneratedPage;

  expect(generatedData.entity_name).toBe(ENTITY);
  expect(generatedData.total_rows).toBe(TARGET_ROWS);
  expect(generatedData.rows).toHaveLength(TARGET_ROWS);

  scenario = {
    ...model,
    jobId: jobMatch![1],
    generatedData,
  };
}

async function openScenarioModel(page: Page): Promise<Scenario> {
  const current = requireScenario();
  await page.goto(current.modelUrl);
  await expect(
    page.locator('app-model-studio-entity-node').filter({
      hasText: ENTITY,
    }),
  ).toBeVisible();
  return current;
}

async function deleteScenarioModel(): Promise<void> {
  if (!setupContext || !createdModelName) {
    return;
  }

  const page = await setupContext.newPage();

  try {
    await page.goto('/workspace');
    await expect(page.locator('app-workspace')).toBeVisible();

    const card = page.locator('.dataModel-card').filter({
      has: page.getByRole('heading', {
        name: createdModelName,
        exact: true,
      }),
    });

    const count = await card.count();
    if (count === 0) {
      return;
    }

    expect(
      count,
      'Cleanup must identify exactly one MS08-owned model before deletion',
    ).toBe(1);

    await card.getByRole('button', {
      name: 'Edit Data Model',
    }).click();

    const editDialog = page.getByRole('dialog', {
      name: 'Edit Data Model',
    });

    await expect(editDialog).toBeVisible();
    await editDialog.locator('button.delete-button').click();

    const confirmation = page.getByRole('dialog', {
      name: 'Delete this Data Model?',
    });

    await expect(confirmation).toBeVisible();
    await expect(confirmation).toContainText(createdModelName);

    const confirmButton = confirmation.locator('button.confirm-button');
    await expect(confirmButton).toBeEnabled();
    await confirmButton.click();

    await expect(card).toHaveCount(0, { timeout: 30_000 });
  } finally {
    await page.close();
  }
}

test.describe('MS08 - Field type and generation configuration', () => {
  test.describe.configure({ timeout: 600_000 });

  test.beforeAll(async ({ browser }) => {
    await prepareScenario(browser);
  });

  test.afterAll(async () => {
    try {
      await deleteScenarioModel();
    } finally {
      await setupContext?.close();
      setupContext = undefined;
    }
  });

  test('MS08-01: IDENTIFIER generates sequential identity values', async ({
    page,
  }, testInfo) => {
    const current = await openScenarioModel(page);
    const rows = current.generatedData.rows;
    const ids = numericValues(rows, 'RECORD_ID');

    expect(new Set(ids).size).toBe(TARGET_ROWS);
    for (let index = 1; index < ids.length; index += 1) {
      expect(ids[index]).toBe(ids[index - 1] + 1);
    }

    await testInfo.attach('ms08-01-identity-values.json', {
      body: JSON.stringify(ids, null, 2),
      contentType: 'application/json',
    });
  });

  test('MS08-02: RANDOM_STRING respects configured length', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);

    for (const row of current.generatedData.rows) {
      expect(row.RANDOM_TEXT).not.toBeNull();
      expect(row.RANDOM_TEXT!.length).toBeGreaterThanOrEqual(5);
      expect(row.RANDOM_TEXT!.length).toBeLessThanOrEqual(10);
    }
  });

  test('MS08-03: ALPHA contains letters only', async ({ page }) => {
    const current = await openScenarioModel(page);

    for (const row of current.generatedData.rows) {
      expect(row.ALPHA_TEXT).toMatch(/^[A-Za-z]{8}$/);
    }
  });

  test('MS08-04: DIGITS contains numeric characters only', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);

    for (const row of current.generatedData.rows) {
      expect(row.DIGITS_TEXT).toMatch(/^\d{8}$/);
    }
  });

  test('MS08-05: ALPHANUMERIC contains only permitted characters', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);

    for (const row of current.generatedData.rows) {
      expect(row.ALNUM_TEXT).toMatch(/^[A-Za-z0-9]{8}$/);
    }
  });

  test('MS08-06: Minimum and maximum string lengths are respected', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);

    for (const row of current.generatedData.rows) {
      const value = row.BOUNDED_TEXT!;
      expect(value.length).toBeGreaterThanOrEqual(6);
      expect(value.length).toBeLessThanOrEqual(12);
    }
  });

  test('MS08-07: PATTERN generator follows configured tokens', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);

    for (const row of current.generatedData.rows) {
      expect(row.TOKEN_PATTERN).toMatch(
        /^ORD-\d[A-Z]{2}-[a-z]{2}-[A-Za-z0-9]{2}$/,
      );
    }
  });

  test('MS08-08: PATTERN generator preserves literal characters', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);

    for (const row of current.generatedData.rows) {
      expect(row.LITERAL_PATTERN).toMatch(/^INV-\d{4}-US$/);
    }
  });

  test('MS08-09: SEMANTIC UNIQUE generates distinct non-empty values', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);
    const values = current.generatedData.rows.map(
      (row) => row.UNIQUE_DESCRIPTION ?? '',
    );

    expect(values).toHaveLength(TARGET_ROWS);
    expect(values.every((value) => value.trim().length > 0)).toBe(true);
    expect(new Set(values).size).toBe(TARGET_ROWS);
  });

  test('MS08-10: SEMANTIC VOCABULARY values belong to persisted vocabulary', async ({
    page,
  }, testInfo) => {
    const current = await openScenarioModel(page);
    const values = current.generatedData.rows.map(
      (row) => row.PRODUCT_CATEGORY ?? '',
    );

    expect(values).toHaveLength(TARGET_ROWS);
    expect(values.every((value) => value.trim().length > 0)).toBe(true);

    const candidateId = process.env.FORGE_E2E_CANDIDATE_ID;
    if (!candidateId) {
      throw new Error(
        'FORGE_E2E_CANDIDATE_ID is required to verify persisted semantic vocabulary.',
      );
    }

    const semanticPath = resolve(
      __dirname,
      '../../../dist/test-runs',
      candidateId,
      'runtime/forge-deployment/backend/api/data/data_model',
      current.modelId,
      'generation',
      current.jobId,
      'semantic.json',
    );

    const semanticDocument = JSON.parse(
      readFileSync(semanticPath, 'utf8'),
    ) as {
      job_id?: string;
      fields?: Record<string, {
        mode?: string;
        values?: string[];
      }>;
    };

    expect(semanticDocument.job_id).toBe(current.jobId);

    const vocabularyRecord =
      semanticDocument.fields?.[`${ENTITY}.PRODUCT_CATEGORY`];

    expect(vocabularyRecord).toBeTruthy();
    if (!vocabularyRecord) {
      throw new Error(
        `Persisted semantic vocabulary is missing for ${ENTITY}.PRODUCT_CATEGORY.`,
      );
    }

    expect(vocabularyRecord.mode).toBe('VOCABULARY');
    expect(vocabularyRecord.values).toHaveLength(50);

    const vocabularyValues = vocabularyRecord.values!;
    expect(
      vocabularyValues.every(
        (value) => typeof value === 'string' && value.trim().length > 0,
      ),
    ).toBe(true);

    const vocabulary = new Set(vocabularyValues);
    const outOfVocabulary = [...new Set(values)].filter(
      (value) => !vocabulary.has(value),
    );

    expect(
      outOfVocabulary,
      'Every generated PRODUCT_CATEGORY value must belong to the persisted 50-value semantic vocabulary.',
    ).toEqual([]);

    const origin = new URL(page.url()).origin;
    const response = await page.context().request.get(
      `${origin}/api/v1/data-models/${current.modelId}/generation/${current.jobId}`,
      {
        headers: await getApiAuthorizationHeaders(page),
      },
    );

    expect(response.status()).toBe(200);

    const job = await response.json() as {
      entities?: Array<{
        entity_name: string;
        vocabulary_semantic_calls?: Array<{
          field: string;
          requested_count: number;
          returned_count: number;
        }>;
      }>;
    };

    const entityProgress = job.entities?.find(
      (entity) => entity.entity_name === ENTITY,
    );

    expect(entityProgress).toBeTruthy();

    const vocabularyCalls = (
      entityProgress?.vocabulary_semantic_calls ?? []
    ).filter((call) => call.field === 'PRODUCT_CATEGORY');

    expect(vocabularyCalls.length).toBeGreaterThan(0);

    const returnedCount = vocabularyCalls.reduce(
      (total, call) => total + call.returned_count,
      0,
    );

    expect(returnedCount).toBeGreaterThanOrEqual(50);

    await testInfo.attach('ms08-vocabulary-verification.json', {
      body: JSON.stringify({
        model_id: current.modelId,
        job_id: current.jobId,
        field: `${ENTITY}.PRODUCT_CATEGORY`,
        mode: vocabularyRecord.mode,
        vocabulary_size: vocabularyValues.length,
        generated_rows: values.length,
        generated_distinct_values: new Set(values).size,
        out_of_vocabulary_values: outOfVocabulary,
        semantic_calls: vocabularyCalls,
        semantic_artifact: semanticPath,
      }, null, 2),
      contentType: 'application/json',
    });
  });

  test('MS08-11: INTEGER UNIFORM values remain within bounds', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);

    for (const value of numericValues(
      current.generatedData.rows,
      'INTEGER_UNIFORM',
    )) {
      expect(Number.isInteger(value)).toBe(true);
      expect(value).toBeGreaterThanOrEqual(10);
      expect(value).toBeLessThanOrEqual(20);
    }
  });

  test('MS08-12: INTEGER DISCRETE_UNIFORM values remain within bounds', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);

    for (const value of numericValues(
      current.generatedData.rows,
      'INTEGER_DISCRETE',
    )) {
      expect(Number.isInteger(value)).toBe(true);
      expect(value).toBeGreaterThanOrEqual(100);
      expect(value).toBeLessThanOrEqual(200);
    }
  });

  test('MS08-13: DECIMAL UNIFORM values remain within bounds', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);

    for (const value of numericValues(
      current.generatedData.rows,
      'DECIMAL_UNIFORM',
    )) {
      expect(value).toBeGreaterThanOrEqual(1);
      expect(value).toBeLessThanOrEqual(9.99);
    }
  });

  test('MS08-14: DECIMAL NORMAL values remain within bounds', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);

    for (const value of numericValues(
      current.generatedData.rows,
      'DECIMAL_NORMAL',
    )) {
      expect(value).toBeGreaterThanOrEqual(1);
      expect(value).toBeLessThanOrEqual(9.99);
    }
  });

  test('MS08-15: DECIMAL precision and scale are respected', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);
    const fields = await getCanonicalFields(page, current.modelId);

    expect(
      fields.find((field) => field.name === 'DECIMAL_GRID'),
    ).toMatchObject({
      type: 'DECIMAL',
      generation: {
        parameters: {
          precision: 6,
          scale: 2,
        },
      },
    });

    for (const row of current.generatedData.rows) {
      const rawValue = row.DECIMAL_GRID;
      expect(rawValue).not.toBeNull();

      const value = Number(rawValue);
      expect(value).toBeGreaterThanOrEqual(1);
      expect(value).toBeLessThanOrEqual(9.99);
      expect(
        Math.abs(value * 100 - Math.round(value * 100)),
      ).toBeLessThan(1e-9);
    }
  });

  test('MS08-16: DECIMAL values work without precision and scale', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);
    const fields = await getCanonicalFields(page, current.modelId);

    for (const fieldName of ['DECIMAL_UNIFORM', 'DECIMAL_NORMAL']) {
      const field = fields.find((item) => item.name === fieldName);
      expect(field).toBeTruthy();
      expect(field!.generation?.parameters?.precision).toBeUndefined();
      expect(field!.generation?.parameters?.scale).toBeUndefined();

      for (const value of numericValues(
        current.generatedData.rows,
        fieldName,
      )) {
        expect(value).toBeGreaterThanOrEqual(1);
        expect(value).toBeLessThanOrEqual(9.99);
      }
    }
  });

  test('MS08-17: BOOLEAN configuration produces valid boolean values', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);
    const fields = await getCanonicalFields(page, current.modelId);

    expect(
      fields.find((field) => field.name === 'IS_ACTIVE'),
    ).toMatchObject({
      type: 'BOOLEAN',
      generation: { strategy: 'RANDOM' },
    });

    for (const row of current.generatedData.rows) {
      expect(row.IS_ACTIVE).not.toBeNull();
      expect(['true', 'false']).toContain(row.IS_ACTIVE!.toLowerCase());
    }
  });

  test('MS08-18: CATEGORICAL values belong to the configured set', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);
    const fields = await getCanonicalFields(page, current.modelId);

    expect(
      fields.find((field) => field.name === 'PRODUCT_TIER'),
    ).toMatchObject({
      type: 'CATEGORICAL',
      generation: {
        strategy: 'RANDOM',
        distribution: 'CATEGORICAL',
        parameters: {
          values: ['Bronze', 'Silver', 'Gold'],
        },
      },
    });

    const allowedValues = new Set(['Bronze', 'Silver', 'Gold']);
    for (const row of current.generatedData.rows) {
      expect(row.PRODUCT_TIER).not.toBeNull();
      expect(allowedValues.has(row.PRODUCT_TIER!)).toBe(true);
    }
  });

  test('MS08-19: Field configuration persists after reload', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);
    const fieldsBeforeReload = await getCanonicalFields(
      page,
      current.modelId,
    );

    const expectedTypes = [
      'IDENTIFIER',
      'STRING',
      'INTEGER',
      'DECIMAL',
      'BOOLEAN',
      'CATEGORICAL',
    ];

    expect(
      [...new Set(fieldsBeforeReload.map((field) => field.type))].sort(),
    ).toEqual([...expectedTypes].sort());

    const beforeReload = fieldsBeforeReload
      .map((field) => ({
        name: field.name,
        type: field.type,
        identity: field.identity,
        generation: field.generation,
      }))
      .sort((a, b) => a.name.localeCompare(b.name));

    await page.reload();

    await expect(
      page.locator('app-model-studio-entity-node').filter({
        hasText: ENTITY,
      }),
    ).toBeVisible();

    const fieldsAfterReload = await getCanonicalFields(
      page,
      current.modelId,
    );

    const afterReload = fieldsAfterReload
      .map((field) => ({
        name: field.name,
        type: field.type,
        identity: field.identity,
        generation: field.generation,
      }))
      .sort((a, b) => a.name.localeCompare(b.name));

    expect(afterReload).toEqual(beforeReload);
  });

  test('MS08-20: UI prevents invalid categorical configuration', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);
    const dialog = await openCategoricalFieldDialog(page);

    await dialog.locator('#field-name').fill('INVALID_CATEGORIES');
    await dialog.getByText('Choice / Category', {
      exact: true,
    }).click();

    const saveButton = dialog.locator('.save-button');
    const categoryInput = dialog.locator('#categorical-values');

    await expect(saveButton).toBeDisabled();

    await categoryInput.fill('Bronze, Silver, Bronze');
    await expect(saveButton).toBeDisabled();

    await categoryInput.fill('Bronze, Silver, Gold');
    await expect(saveButton).toBeEnabled();

    await categoryInput.fill('Bronze, Silver, Bronze');
    await expect(saveButton).toBeDisabled();

    await dialog.getByRole('button', {
      name: /cancel/i,
    }).click();

    await expect(dialog).not.toBeVisible();

    const fields = await getCanonicalFields(page, current.modelId);
    expect(
      fields.some((field) => field.name === 'INVALID_CATEGORIES'),
    ).toBe(false);
  });

  test('MS08-21: API rejects unsupported POISSON distributions', async ({
    page,
  }) => {
    const current = await openScenarioModel(page);
    const origin = new URL(page.url()).origin;
    const endpoint =
      `${origin}/api/v1/data-models/${current.modelId}` +
      `/specification/entities/${encodeURIComponent(ENTITY)}/fields`;

    for (const field of [
      { name: 'INVALID_INTEGER_POISSON', type: 'INTEGER' },
      { name: 'INVALID_DECIMAL_POISSON', type: 'DECIMAL' },
    ]) {
      const response = await page.context().request.post(endpoint, {
        headers: await getApiAuthorizationHeaders(page),
        data: {
          name: field.name,
          type: field.type,
          generation: {
            strategy: 'RANDOM',
            distribution: 'POISSON',
            parameters: {
              minimum: 1,
              maximum: 10,
            },
          },
        },
      });

      expect(
        response.status(),
        `${field.type} POISSON should be rejected`,
      ).toBe(422);

      const body = await response.json();
      expect(body.detail).toBeTruthy();
    }

    const persistedFields = await getCanonicalFields(
      page,
      current.modelId,
    );

    expect(
      persistedFields.some(
        (field) => field.name === 'INVALID_INTEGER_POISSON',
      ),
    ).toBe(false);

    expect(
      persistedFields.some(
        (field) => field.name === 'INVALID_DECIMAL_POISSON',
      ),
    ).toBe(false);
  });
});

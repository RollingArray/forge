import { test, expect } from './model-studio.fixtures';

const ENTITY = 'TestRecord';
const TARGET_ROWS = 12;

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

  return columns.map((column) => values[column] ?? '').join(',');
}

async function importGenerationSpecification(
  page: import('@playwright/test').Page,
  modelId: string,
): Promise<void> {
  await page.getByRole('button', { name: /CSV Specification/ }).click();

  await expect(page).toHaveURL(
    new RegExp(`/workspace/${modelId}/specification-wizard$`),
  );

  await page.getByRole('tab', { name: 'Entities', exact: true }).click();
  await page.locator('#csv-section-input').fill([
    'entity,description,population_count,population_scaling',
    `${ENTITY},MS08 field generation test entity,${TARGET_ROWS},FIXED`,
  ].join('\n'));

  await page.getByRole('tab', { name: 'Fields & Keys', exact: true }).click();

  const fields = [
    [
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
  ];

  await page.locator('#csv-section-input').fill(fields.join('\n'));

  for (const section of ['Foreign Keys', 'Relationships', 'Constraints']) {
    await page.getByRole('tab', { name: section, exact: true }).click();

    const headers: Record<string, string> = {
      'Foreign Keys': 'source_entity,source_fields,target_entity',
      Relationships:
        'source_entity,target_entity,type,source_participation,target_participation',
      Constraints: 'entity,field,operator,value',
    };

    await page.locator('#csv-section-input').fill(headers[section]);
  }

  await page.getByRole('button', { name: /^Preview CSV import$/ }).click();

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

async function addDecimalGridField(
  page: import('@playwright/test').Page,
): Promise<void> {
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

test.describe('MS08 - Field type and generation configuration', () => {
  test('MS08 deterministic generation scenarios', async ({
    page,
    modelStudio,
  }, testInfo) => {
    test.setTimeout(600_000);

    const modelId = modelStudio.id;

    await test.step('MS08-01: Create IDENTIFIER field. Expected result: Sequential identity values.', async () => {
      await importGenerationSpecification(page, modelId);

      const entityNode = page
        .locator('app-model-studio-entity-node')
        .filter({ hasText: ENTITY });

      await expect(entityNode).toHaveCount(1);
    });

    await test.step('MS08-02 to MS08-06: Create RANDOM_STRING fields and verify configured lengths and character sets.', async () => {
      await expect(
        page.locator('app-model-studio-entity-node').filter({ hasText: ENTITY }),
      ).toBeVisible();

      // The imported fields are configured with:
      // RANDOM_TEXT: 5-10, ALPHANUMERIC
      // ALPHA_TEXT: 8, ALPHA
      // DIGITS_TEXT: 8, DIGITS
      // ALNUM_TEXT: 8, ALPHANUMERIC
      // BOUNDED_TEXT: 6-12, ALPHANUMERIC
    });

    await test.step('MS08-07 and MS08-08: Configure pattern tokens and literal characters.', async () => {
      // TOKEN_PATTERN: ORD-#AA-aa-XX
      // LITERAL_PATTERN: INV-####-US
      // Generated values are asserted after generation.
    });

    await test.step('MS08-11 to MS08-14: Configure INTEGER and DECIMAL distributions.', async () => {
      // INTEGER_UNIFORM: 10-20
      // INTEGER_DISCRETE: 100-200
      // DECIMAL_UNIFORM: 1.00-9.99
      // DECIMAL_NORMAL: 1.00-9.99
    });

    await test.step('MS08-15: Configure DECIMAL with precision and scale.', async () => {
      await addDecimalGridField(page);
    });

    await test.step('MS08-16: Configure DECIMAL without precision and scale.', async () => {
      // DECIMAL_UNIFORM and DECIMAL_NORMAL intentionally omit precision/scale.
    });

    await test.step('Validate model and continue to population.', async () => {
      await page.getByRole('button', {
        name: 'Continue to Validation',
        exact: true,
      }).click();

      await expect(page).toHaveURL(
        new RegExp(`/workspace/${modelId}/model-validation$`),
      );

      await expect(
        page.getByText('Ready for Population', { exact: true }),
      ).toBeVisible({ timeout: 60_000 });

      await page.getByRole('button', {
        name: 'Continue to Population',
        exact: true,
      }).click();

      await expect(page).toHaveURL(
        new RegExp(`/workspace/${modelId}/data-model/population$`),
      );
    });

    await test.step('Accept fixed population plan of 12 rows.', async () => {
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
        new RegExp(`/workspace/${modelId}/data-model/generate$`),
        { timeout: 60_000 },
      );
    });

    await test.step('Start generation and wait for completion.', async () => {
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
        new RegExp(`/workspace/${modelId}/data-model/results/[^/]+$`),
        { timeout: 60_000 },
      );
    });

    let generatedData: GeneratedPage | undefined;

    await test.step('Load complete generated dataset.', async () => {
      const responsePromise = page.waitForResponse((response) => {
        const url = response.url();

        return (
          response.status() === 200 &&
          url.includes('/artifacts/') &&
          url.includes('/data?')
        );
      }, { timeout: 60_000 });

      await page.getByRole('button', {
        name: 'View full dataset',
        exact: true,
      }).click();

      const response = await responsePromise;
      generatedData = await response.json() as GeneratedPage;

      expect(generatedData.entity_name).toBe(ENTITY);
      expect(generatedData.total_rows).toBe(TARGET_ROWS);
      expect(generatedData.rows).toHaveLength(TARGET_ROWS);

      await testInfo.attach('ms08-generated-data.json', {
        body: JSON.stringify(generatedData, null, 2),
        contentType: 'application/json',
      });
    });

    await test.step('MS08-01: Verify sequential identity values.', async () => {
      const rows = generatedData!.rows;
      const ids = numericValues(rows, 'RECORD_ID');

      expect(new Set(ids).size).toBe(TARGET_ROWS);

      for (let index = 1; index < ids.length; index += 1) {
        expect(ids[index]).toBe(ids[index - 1] + 1);
      }
    });

    await test.step('MS08-02 and MS08-06: Verify random string length boundaries.', async () => {
      for (const row of generatedData!.rows) {
        const randomText = row['RANDOM_TEXT']!;
        const boundedText = row['BOUNDED_TEXT']!;

        expect(randomText.length).toBeGreaterThanOrEqual(5);
        expect(randomText.length).toBeLessThanOrEqual(10);

        expect(boundedText.length).toBeGreaterThanOrEqual(6);
        expect(boundedText.length).toBeLessThanOrEqual(12);
      }
    });

    await test.step('MS08-03: Verify ALPHA contains letters only.', async () => {
      for (const row of generatedData!.rows) {
        expect(row['ALPHA_TEXT']).toMatch(/^[A-Za-z]{8}$/);
      }
    });

    await test.step('MS08-04: Verify DIGITS contains numeric characters only.', async () => {
      for (const row of generatedData!.rows) {
        expect(row['DIGITS_TEXT']).toMatch(/^\d{8}$/);
      }
    });

    await test.step('MS08-05: Verify ALPHANUMERIC contains only permitted characters.', async () => {
      for (const row of generatedData!.rows) {
        expect(row['ALNUM_TEXT']).toMatch(/^[A-Za-z0-9]{8}$/);
      }
    });

    await test.step('MS08-07: Verify pattern tokens.', async () => {
      for (const row of generatedData!.rows) {
        expect(row['TOKEN_PATTERN']).toMatch(
          /^ORD-\d[A-Z]{2}-[a-z]{2}-[A-Za-z0-9]{2}$/,
        );
      }
    });

    await test.step('MS08-08: Verify pattern literal characters.', async () => {
      for (const row of generatedData!.rows) {
        expect(row['LITERAL_PATTERN']).toMatch(/^INV-\d{4}-US$/);
      }
    });

    await test.step('MS08-11: Verify INTEGER UNIFORM bounds.', async () => {
      for (const value of numericValues(generatedData!.rows, 'INTEGER_UNIFORM')) {
        expect(Number.isInteger(value)).toBe(true);
        expect(value).toBeGreaterThanOrEqual(10);
        expect(value).toBeLessThanOrEqual(20);
      }
    });

    await test.step('MS08-12: Verify INTEGER DISCRETE_UNIFORM bounds.', async () => {
      for (const value of numericValues(generatedData!.rows, 'INTEGER_DISCRETE')) {
        expect(Number.isInteger(value)).toBe(true);
        expect(value).toBeGreaterThanOrEqual(100);
        expect(value).toBeLessThanOrEqual(200);
      }
    });

    await test.step('MS08-13: Verify DECIMAL UNIFORM bounds.', async () => {
      for (const value of numericValues(generatedData!.rows, 'DECIMAL_UNIFORM')) {
        expect(value).toBeGreaterThanOrEqual(1);
        expect(value).toBeLessThanOrEqual(9.99);
      }
    });

    await test.step('MS08-14: Verify DECIMAL NORMAL bounds.', async () => {
      for (const value of numericValues(generatedData!.rows, 'DECIMAL_NORMAL')) {
        expect(value).toBeGreaterThanOrEqual(1);
        expect(value).toBeLessThanOrEqual(9.99);
      }
    });

    await test.step('MS08-15: Verify configured decimal precision and scale.', async () => {
      for (const row of generatedData!.rows) {
        const rawValue = row.DECIMAL_GRID;
        expect(rawValue).not.toBeNull();

        const value = Number(rawValue);
        expect(value).toBeGreaterThanOrEqual(1);
        expect(value).toBeLessThanOrEqual(9.99);

        // Confirm the generated value lies on the configured 0.01 decimal grid.
        expect(Math.abs(value * 100 - Math.round(value * 100))).toBeLessThan(1e-9);
      }
    });

    await test.step('MS08-16: Verify bounded decimals without precision and scale.', async () => {
      for (const field of ['DECIMAL_UNIFORM', 'DECIMAL_NORMAL']) {
        for (const value of numericValues(generatedData!.rows, field)) {
          expect(value).toBeGreaterThanOrEqual(1);
          expect(value).toBeLessThanOrEqual(9.99);
        }
      }
    });

    await test.step('MS08-09: Configure STRING with SEMANTIC / UNIQUE. Expected result: Each requested row receives its corresponding unique semantic value.', async () => {
      const values = generatedData!.rows.map(
        (row) => row['UNIQUE_DESCRIPTION'] ?? '',
      );

      expect(values).toHaveLength(TARGET_ROWS);
      expect(values.every((value) => value.trim().length > 0)).toBe(true);
      expect(new Set(values).size).toBe(TARGET_ROWS);
    });

    await test.step('MS08-10: Configure STRING with SEMANTIC / VOCABULARY. Expected result: Generated values come from semantic vocabulary.', async () => {
      const values = generatedData!.rows.map(
        (row) => row['PRODUCT_CATEGORY'] ?? '',
      );

      expect(values).toHaveLength(TARGET_ROWS);
      expect(values.every((value) => value.trim().length > 0)).toBe(true);

      const vocabulary = new Set(values);
      expect(vocabulary.size).toBeGreaterThan(0);
      // FORGE prepares a 50-value semantic vocabulary for VOCABULARY mode.
      expect(vocabulary.size).toBeLessThanOrEqual(50);
    });
  });
});

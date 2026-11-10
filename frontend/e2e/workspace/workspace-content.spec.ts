import { test, expect } from './workspace.fixtures';

test.describe('Workspace templates and activity', () => {
  test('WS11-01: renders template cards from the Workspace API', async ({
    page,
  }) => {
    const templatesResponsePromise = page.waitForResponse((response) =>
      response.url().includes('/api/v1/workspace/templates')
      && response.request().method() === 'GET',
    );

    await page.goto('/workspace');

    const response = await templatesResponsePromise;
    expect(response.status()).toBe(200);

    const templates = await response.json() as Array<{
      name: string;
      description: string;
      icon: string;
      accent: string;
    }>;

    const cards = page.locator('app-template-card .template-card');

    await expect(cards).toHaveCount(templates.length);

    for (let index = 0; index < templates.length; index++) {
      const card = cards.nth(index);
      const template = templates[index];

      await expect(card.locator('h3')).toHaveText(template.name);
      await expect(card.locator('p')).toHaveText(template.description);
      await expect(card.locator('.template-icon span'))
        .toHaveText(template.icon);
    }
  });

  test('WS12-01: renders activity entries from the Workspace API', async ({
    page,
  }) => {
    const activityResponsePromise = page.waitForResponse((response) =>
      response.url().includes('/api/v1/workspace/activity')
      && response.request().method() === 'GET',
    );

    await page.goto('/workspace');

    const response = await activityResponsePromise;
    expect(response.status()).toBe(200);

    const activities = await response.json() as Array<{
      action: string;
      description: string;
      data_model: string;
      actor: string;
      target: string | null;
      time: string;
      icon: string;
      accent: string;
    }>;

    const items = page.locator('app-activity-item .activity-item');

    await expect(items).toHaveCount(activities.length);

    for (let index = 0; index < activities.length; index++) {
      const item = items.nth(index);
      const activity = activities[index];

      await expect(item.locator('.activity-action'))
        .toHaveText(activity.action);

      await expect(item.locator('.activity-description'))
        .toHaveText(activity.description);

      await expect(item.locator('.activity-dataModel'))
        .toHaveText(activity.data_model);

      await expect(item.locator('.activity-icon span'))
        .toHaveText(activity.icon);
    }
  });
});

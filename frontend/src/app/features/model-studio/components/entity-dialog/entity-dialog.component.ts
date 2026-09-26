/**
 * File: entity-dialog.component.ts
 * Purpose: Add Entity authoring dialog for Model Studio.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import {
  ChangeDetectionStrategy,
  Component,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import { FormDialogComponent } from '../../../../shared/components/form-dialog/form-dialog.component';

export interface EntityDraft {
  name: string;
  description: string;
  population: number;
}

@Component({
  selector: 'app-model-studio-entity-dialog',
  standalone: true,
  imports: [FormsModule, FormDialogComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-form-dialog
      title="Add Entity"
      subtitle="Define an entity for this Data Model."
      icon="table_view"
      width="1080px"
      (closed)="closed.emit()"
    >
      <div dialog-body class="entity-dialog-body">
        <div class="authoring-layout">

          <section class="ai-panel">
            <div class="recommended-badge">
              <span class="material-symbols-outlined">auto_awesome</span>
              RECOMMENDED
            </div>

            <div class="ai-heading">
              <div class="ai-icon">
                <span class="material-symbols-outlined">auto_awesome</span>
              </div>

              <div>
                <h2>Start with FORGE AI</h2>
                <span class="online-badge">
                  <span class="online-dot"></span>
                  ONLINE
                </span>
              </div>
            </div>

            <p class="ai-description">
              Describe the entity you want to model in natural language.
              FORGE AI will propose a starting point for you to review.
            </p>

            <textarea
              class="ai-prompt"
              [(ngModel)]="aiPrompt"
              placeholder="e.g. Create a CUSTOMER entity representing enterprise customers with 50,000 records."
              maxlength="2000"
            ></textarea>

            <div class="ai-action-row">
              <span class="ai-hint">
                <span class="material-symbols-outlined">lightbulb</span>
                Describe the business entity and expected population.
              </span>

              <button
                type="button"
                class="ai-button"
                [disabled]="!aiPrompt().trim()"
                (click)="requestAiProposal()"
              >
                <span class="material-symbols-outlined">auto_awesome</span>
                Generate with FORGE AI
              </button>
            </div>

            <div class="examples-section">
              <div class="examples-title">
                <span class="material-symbols-outlined">lightbulb</span>
                <strong>Example prompts</strong>
              </div>

              <button
                type="button"
                class="example-prompt"
                (click)="useExample('I need 100 customers.')"
              >
                I need 100 customers.
              </button>

              <button
                type="button"
                class="example-prompt"
                (click)="useExample('Create an SAP customer master table named KNA1 with 100 records.')"
              >
                Create an SAP customer master table named KNA1 with 100 records.
              </button>

              <button
                type="button"
                class="example-prompt"
                (click)="useExample('Create a sales order header entity called VBAK with 200 records.')"
              >
                Create a sales order header entity called VBAK with 200 records.
              </button>
            </div>

            <div class="decision-card">
              <span class="material-symbols-outlined">lightbulb</span>
              <div>
                <strong>AI proposes. You decide.</strong>
                <p>
                  Review the proposed entity before it becomes part of the
                  FORGE specification.
                </p>
              </div>
            </div>
          </section>

          <div class="divider">
            <span>OR</span>
          </div>

          <section class="manual-panel">
            <h2>Enter manually</h2>
            <p class="manual-intro">
              Prefer to define the entity yourself? Enter the details below.
            </p>

            <label class="field-label" for="entity-name">
              Entity Name
            </label>
            <p class="field-help">
              Give the entity a clear name that identifies the business
              process, system, or table it represents.
              <span class="field-example">Examples: CUSTOMER, KNA1, VBAK</span>
            </p>

            <input
              id="entity-name"
              class="field-input"
              type="text"
              [(ngModel)]="name"
              maxlength="120"
              placeholder="e.g. CUSTOMER"
            />

            <label class="field-label" for="entity-description">
              Description
            </label>
            <p class="field-help">
              Describe what this entity represents.
              <span class="field-example">
                Examples: Customer master data, Sales order header, Product catalog
              </span>
            </p>

            <textarea
              id="entity-description"
              class="field-input description-input"
              [(ngModel)]="description"
              maxlength="500"
              placeholder="Describe the entity."
            ></textarea>

            <label class="field-label" for="entity-population">
              Population
            </label>
            <p class="field-help">
              Specify the number of records FORGE should engineer for this
              entity.
              <span class="field-example">Examples: 100, 10,000, 50,000</span>
            </p>

            <div class="population-input">
              <input
                id="entity-population"
                class="field-input"
                type="number"
                min="0"
                step="1"
                [(ngModel)]="population"
              />
              <span>records</span>
            </div>
          </section>

        </div>
      </div>

      <div dialog-footer class="dialog-footer">
        <button
          type="button"
          class="secondary-button"
          (click)="closed.emit()"
        >
          Cancel
        </button>

        <button
          type="button"
          class="primary-button"
          [disabled]="!canSave()"
          (click)="save()"
        >
          Add Entity
        </button>
      </div>
    </app-form-dialog>
  `,
  styles: [`
    :host {
      display: block;
    }

    .entity-dialog-body {
      width: 100%;
    }

    .authoring-layout {
      display: grid;
      grid-template-columns: minmax(0, 1.08fr) 42px minmax(360px, 0.92fr);
      min-height: 610px;
    }

    .ai-panel {
      padding: 28px 28px 30px;
      background: linear-gradient(145deg, #faf7ff 0%, #f7f4ff 100%);
      border: 1px solid #e6ddff;
      border-radius: 18px;
    }

    .recommended-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border: 1px solid #d8caff;
      border-radius: 999px;
      color: #6547cf;
      background: #f5efff;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.08em;
    }

    .recommended-badge .material-symbols-outlined {
      font-size: 14px;
    }

    .ai-heading {
      display: flex;
      align-items: center;
      gap: 14px;
      margin-top: 20px;
    }

    .ai-icon {
      width: 52px;
      height: 52px;
      display: grid;
      place-items: center;
      border-radius: 14px;
      background: #7352d8;
      color: white;
      box-shadow: 0 8px 18px rgba(83, 55, 170, 0.22);
      flex: 0 0 auto;
    }

    .ai-icon .material-symbols-outlined {
      font-size: 28px;
    }

    .ai-heading h2 {
      display: inline;
      margin: 0 8px 0 0;
      color: #292540;
      font-size: 20px;
      font-weight: 700;
    }

    .online-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 8px;
      border-radius: 999px;
      background: #edf9f1;
      border: 1px solid #ccead5;
      color: #27814c;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.08em;
      vertical-align: middle;
    }

    .online-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #32a85d;
    }

    .ai-description {
      margin: 12px 0 18px 66px;
      color: #77748a;
      font-size: 13px;
      line-height: 1.5;
    }

    .ai-prompt {
      width: 100%;
      min-height: 150px;
      resize: vertical;
      box-sizing: border-box;
      padding: 16px;
      border: 1px solid #ddd4f4;
      border-radius: 14px;
      background: white;
      color: #302d3d;
      font: inherit;
      outline: none;
    }

    .ai-prompt:focus,
    .field-input:focus {
      border-color: #8367df;
      box-shadow: 0 0 0 3px rgba(115, 82, 216, 0.10);
    }

    .ai-action-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 12px;
      margin-top: -1px;
      border: 1px solid #ddd4f4;
      border-top: 0;
      border-radius: 0 0 14px 14px;
      background: #f5f0ff;
    }

    .ai-hint {
      display: flex;
      align-items: center;
      gap: 5px;
      color: #8a849d;
      font-size: 10px;
    }

    .ai-hint .material-symbols-outlined {
      font-size: 17px;
      color: #795bd5;
    }

    .ai-button {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      border: 0;
      border-radius: 10px;
      padding: 11px 15px;
      background: #7556d8;
      color: white;
      font: inherit;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
    }

    .ai-button:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }

    .ai-button .material-symbols-outlined {
      font-size: 17px;
    }

    .examples-section {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 20px;
      padding: 16px;
      border: 1px solid #e5def4;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.65);
    }

    .examples-title {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 3px;
      color: #5c5870;
      font-size: 12px;
    }

    .examples-title .material-symbols-outlined {
      color: #7556d8;
      font-size: 19px;
    }

    .example-prompt {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #e5def4;
      border-radius: 9px;
      background: white;
      color: #666276;
      text-align: left;
      font: inherit;
      font-size: 11px;
      line-height: 1.4;
      cursor: pointer;
    }

    .example-prompt:hover {
      border-color: #b9a6ed;
      background: #faf8ff;
      color: #5f45bd;
    }

    .decision-card {
      display: flex;
      gap: 12px;
      margin-top: 20px;
      padding: 16px;
      border: 1px dashed #e5def4;
      border-radius: 12px;
      background: transparent;
      color: #68647a;
    }

    .decision-card .material-symbols-outlined {
      color: #7556d8;
      font-size: 20px;
      flex: 0 0 auto;
    }

    .decision-card strong {
      color: #5c5870;
      font-size: 12px;
    }

    .decision-card p {
      margin: 5px 0 0;
      font-size: 11px;
      line-height: 1.45;
    }

    .divider {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 42px;
      margin: 0 14px;
    }

    .divider::before {
      content: '';
      position: absolute;
      inset: 0 auto 0 50%;
      width: 1px;
      background: #ddd7e8;
    }

    .divider span {
      position: relative;
      z-index: 1;
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border: 1px solid #d7c8ff;
      border-radius: 50%;
      background: #eee8ff;
      color: #7352d8;
      font-size: 10px;
      font-weight: 700;
    }

    .manual-panel {
      padding: 28px 28px 30px;
    }

    .manual-panel h2 {
      margin: 0;
      color: #39354a;
      font-size: 17px;
      font-weight: 700;
    }

    .manual-intro {
      margin: 6px 0 26px;
      color: #8a8795;
      font-size: 12px;
      line-height: 1.45;
    }

    .field-label {
      display: block;
      margin: 0 0 7px;
      color: #3b3749;
      font-size: 13px;
      font-weight: 700;
    }

    .field-help {
      margin: 0 0 9px;
      color: #8b8795;
      font-size: 11px;
      line-height: 1.4;
    }

    .field-example {
      display: block;
      margin-top: 3px;
      color: #a09baa;
      font-style: italic;
    }

    .field-input {
      width: 100%;
      box-sizing: border-box;
      margin-bottom: 22px;
      padding: 13px 14px;
      border: 1px solid #ddd9e2;
      border-radius: 10px;
      background: white;
      color: #353142;
      font: inherit;
      font-size: 13px;
      outline: none;
    }

    .description-input {
      min-height: 115px;
      resize: vertical;
    }

    .population-input {
      position: relative;
      display: flex;
      align-items: center;
    }

    .population-input .field-input {
      margin-bottom: 0;
      padding-right: 72px;
    }

    .population-input span {
      position: absolute;
      right: 14px;
      color: #8a8795;
      font-size: 11px;
      pointer-events: none;
    }

    .dialog-footer {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 12px;
      width: 100%;
      box-sizing: border-box;
      padding: 18px 28px;
      background: #f5f0e9;
      border-top: 1px solid #e3ddd5;
    }

    .secondary-button,
    .primary-button {
      min-width: 120px;
      padding: 12px 20px;
      border-radius: 10px;
      font: inherit;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
    }

    .secondary-button {
      border: 1px solid #ddd9e2;
      background: white;
      color: #5c6175;
    }

    .primary-button {
      border: 0;
      background: #7352d8;
      color: white;
    }

    .primary-button:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }

    @media (max-width: 900px) {
      .authoring-layout {
        grid-template-columns: 1fr;
      }

      .divider {
        width: auto;
        height: 42px;
        margin: 8px 28px;
      }

      .divider::before {
        inset: 50% 0 auto;
        width: auto;
        height: 1px;
      }
    }
  `],
})
export class EntityDialogComponent {
  readonly saved = output<EntityDraft>();
  readonly aiRequested = output<string>();
  readonly closed = output<void>();

  readonly name = signal('');
  readonly description = signal('');
  readonly population = signal<number>(100);
  readonly aiPrompt = signal('');

  canSave(): boolean {
    return (
      this.name().trim().length > 0 &&
      Number.isInteger(this.population()) &&
      this.population() >= 0
    );
  }

  save(): void {
    if (!this.canSave()) {
      return;
    }

    this.saved.emit({
      name: this.name().trim(),
      description: this.description().trim(),
      population: this.population(),
    });
  }

  useExample(prompt: string): void {
    this.aiPrompt.set(prompt);
  }

  requestAiProposal(): void {
    const prompt = this.aiPrompt().trim();

    if (prompt) {
      this.aiRequested.emit(prompt);
    }
  }
}

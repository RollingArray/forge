import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { CanvasEntity } from '../../models/model-studio.models';

@Component({
  selector: 'app-model-studio-entity-node',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <button
      type="button"
      class="entity-node"
      [class.selected]="selected()"
      [class.blue]="entity().accent === 'blue'"
      [class.green]="entity().accent === 'green'"
      [class.amber]="entity().accent === 'amber'"
      [class.pink]="entity().accent === 'pink'"
      [class.purple]="entity().accent === 'purple'"
      [class.orange]="entity().accent === 'orange'"
      [class.teal]="entity().accent === 'teal'"
      [class.cyan]="entity().accent === 'cyan'"
      [class.indigo]="entity().accent === 'indigo'"
      [class.rose]="entity().accent === 'rose'"
      (click)="select()"
    >
      <div class="entity-header">
        <div class="entity-title">
          <span class="material-symbols-outlined entity-icon">
            database
          </span>

          <strong>
            {{ entity().name }}
          </strong>
        </div>

        <span class="material-symbols-outlined menu-icon">
          more_vert
        </span>
      </div>

      <div class="entity-summary">
        <div class="summary-row">
          <span class="material-symbols-outlined summary-icon">
            table_rows
          </span>

          <span class="summary-label">
            {{ entity().fields.length }} fields
          </span>
        </div>

        <div class="summary-row">
          <span class="material-symbols-outlined summary-icon">
            key
          </span>

          <span class="summary-label">
            {{ entity().keyCount }} keys
          </span>
        </div>

        <div class="summary-row">
          <span class="material-symbols-outlined summary-icon">
            account_tree
          </span>

          <span class="summary-label">
            {{ entity().relationshipCount }} relationships
          </span>
        </div>

        <div class="summary-row">
          <span class="material-symbols-outlined summary-icon">
            rule
          </span>

          <span class="summary-label">
            {{ entity().constraintCount }} constraints
          </span>
        </div>
      </div>
    </button>
  `,
  styles: [`
    :host {
      position: absolute;
      display: block;
      width: 230px;
      height: 210px;
      z-index: 10;
    }

    .entity-node {
      display: flex;
      width: 230px;
      height: 210px;
      min-width: 230px;
      min-height: 210px;
      max-width: 230px;
      max-height: 210px;
      box-sizing: border-box;
      flex-direction: column;
      padding: 0;
      border: 1px solid #dfe3ec;
      border-radius: 10px;
      background: #ffffff;
      color: #18203d;
      font-family: inherit;
      text-align: left;
      box-shadow: 0 2px 8px rgba(35, 45, 75, 0.05);
      cursor: pointer;
      overflow: hidden;
      transition:
        border-color 150ms ease,
        box-shadow 150ms ease;
    }

    .entity-node:hover {
      border-color: #bfc5d6;
      box-shadow: 0 5px 14px rgba(35, 45, 75, 0.09);
    }

    .entity-node.selected {
      border-color: #655ce7;
      box-shadow:
        0 0 0 1px #655ce7,
        0 5px 16px rgba(91, 83, 220, 0.12);
    }

    .entity-header {
      display: flex;
      width: 100%;
      height: 54px;
      min-height: 54px;
      box-sizing: border-box;
      align-items: center;
      justify-content: space-between;
      padding: 0 14px;
      border-bottom: 1px solid
        color-mix(
          in srgb,
          var(--entity-accent) 25%,
          transparent
        );
      background: var(--entity-accent-soft);
    }

    .entity-title {
      display: flex;
      min-width: 0;
      align-items: center;
      gap: 9px;
      color: var(--entity-accent);
    }

    .entity-icon {
      flex: 0 0 auto;
      color: var(--entity-accent);
      font-size: 20px;
    }

    .entity-title strong {
      min-width: 0;
      overflow: hidden;
      color: var(--entity-accent);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.2px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .menu-icon {
      flex: 0 0 auto;
      color: #727a96;
      font-size: 18px;
    }

    .entity-summary {
      display: flex;
      flex: 1;
      flex-direction: column;
      justify-content: center;
      gap: 10px;
      padding: 18px 16px;
    }

    .summary-row {
      display: flex;
      height: 25px;
      align-items: center;
      gap: 10px;
      color: #58627f;
    }

    .summary-icon {
      flex: 0 0 auto;
      color: var(--entity-accent);
      font-size: 18px;
    }

    .summary-label {
      overflow: hidden;
      color: #58627f;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.1px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .entity-node.blue {
      --entity-accent: #4f6df5;
      --entity-accent-soft: #eef2ff;
    }

    .entity-node.green {
      --entity-accent: #25a56a;
      --entity-accent-soft: #eaf8f1;
    }

    .entity-node.orange {
      --entity-accent: #e79520;
      --entity-accent-soft: #fff4df;
    }

    .entity-node.pink {
      --entity-accent: #e85b9f;
      --entity-accent-soft: #fff0f7;
    }

    .entity-node.purple {
      --entity-accent: #8b6bd9;
      --entity-accent-soft: #f3efff;
    }

    .entity-node.teal {
      --entity-accent: #159f9a;
      --entity-accent-soft: #e8f8f7;
    }

    .entity-node.amber {
      --entity-accent: #d49a18;
      --entity-accent-soft: #fff8df;
    }

    .entity-node.cyan {
      --entity-accent: #269bc5;
      --entity-accent-soft: #eaf7fc;
    }

    .entity-node.indigo {
      --entity-accent: #5b5fc7;
      --entity-accent-soft: #eff0ff;
    }

    .entity-node.rose {
      --entity-accent: #d95772;
      --entity-accent-soft: #fff0f3;
    }
  `],
})
export class EntityNodeComponent {
  readonly entity = input.required<CanvasEntity>();
  readonly selected = input(false);
  readonly selectedChange = output<string>();

  select(): void {
    this.selectedChange.emit(this.entity().name);
  }
}

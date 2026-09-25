/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: template-card.component.ts
 * Purpose: Defines the template card Workspace component.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { Template } from '../../../../core/interfaces/template.interface';

@Component({
  selector: 'app-template-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './template-card.component.html',
  styleUrl: './template-card.component.css',
})
export class TemplateCardComponent {
  readonly template = input.required<Template>();

  readonly use = output<string>();

  useTemplate(): void {
    this.use.emit(this.template().name);
  }
}
